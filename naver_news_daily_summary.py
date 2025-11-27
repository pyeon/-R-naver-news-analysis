import requests
from datetime import datetime, timedelta
import os
from collections import defaultdict
import re
import json
from difflib import SequenceMatcher
import pytz
import pandas as pd
from pathlib import Path
from config import KEYWORDS, DATA_DIR, REPORTS_DIR

# 환경 변수
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID_NEWS')
NAVER_CLIENT_ID = os.environ.get('NAVER_CLIENT_ID')
NAVER_CLIENT_SECRET = os.environ.get('NAVER_CLIENT_SECRET')

# 일일 요약 전용 설정
DAILY_SUMMARY_COUNT = 50

# 유사도 임계값
SIMILARITY_THRESHOLD = float(os.environ.get('SIMILARITY_THRESHOLD', '0.60'))

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

def get_kst_now():
    """현재 한국 시간 반환"""
    return datetime.now(KST)

def get_yesterday_range():
    """전날 00:00:00 ~ 23:59:59 반환"""
    now = get_kst_now()
    yesterday = now - timedelta(days=1)
    
    start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start, end

def parse_pub_date(pub_date_str):
    """네이버 API pubDate를 datetime으로 변환"""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pub_date_str)
        return dt.astimezone(KST)
    except:
        return None

def is_within_date_range(pub_date_str, start_dt, end_dt):
    """뉴스가 특정 날짜 범위 내에 있는지 확인"""
    pub_dt = parse_pub_date(pub_date_str)
    if not pub_dt:
        return False
    
    return start_dt <= pub_dt <= end_dt

def clean_title(title):
    """제목에서 HTML 태그 및 특수문자 제거"""
    title = title.replace('<b>', '').replace('</b>', '')
    title = title.replace('&quot;', '"').replace('&amp;', '&')
    title = title.replace('&lt;', '<').replace('&gt;', '>')
    return title.strip()

def normalize_title(title):
    """제목 정규화 (중복 비교용)"""
    title = clean_title(title)
    title = re.sub(r'\s+', ' ', title)
    return title.lower().strip()

def calculate_similarity(title1, title2):
    """두 제목 간의 유사도 계산 (0.0~1.0)"""
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)
    return SequenceMatcher(None, norm1, norm2).ratio()

def group_similar_news(news_list):
    """유사한 제목의 뉴스를 그룹화"""
    if not news_list:
        return []
    
    groups = []
    used = set()
    
    for i, news in enumerate(news_list):
        if i in used:
            continue
        
        group = [news]
        used.add(i)
        
        for j, other_news in enumerate(news_list):
            if j in used:
                continue
            
            similarity = calculate_similarity(news['title'], other_news['title'])
            
            if similarity >= SIMILARITY_THRESHOLD:
                group.append(other_news)
                used.add(j)
        
        groups.append(group)
    
    return groups

def select_representative_title(group):
    """그룹에서 대표 제목 선택 (가장 정보가 풍부한 제목)"""
    return max(group, key=lambda x: len(clean_title(x['title'])))

def keyword_exists_in_news(news, keyword):
    """뉴스에 키워드가 실제로 포함되어 있는지 확인"""
    title = clean_title(news.get('title', ''))
    description = clean_title(news.get('description', ''))
    
    keyword_lower = keyword.lower()
    title_lower = title.lower()
    description_lower = description.lower()
    
    return keyword_lower in title_lower or keyword_lower in description_lower

def search_naver_news(keyword, start_dt, end_dt):
    """네이버 뉴스 검색 API + 날짜 범위 필터링"""
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {
        "query": keyword,
        "display": DAILY_SUMMARY_COUNT,
        "sort": "date"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            all_items = response.json()['items']
            
            keyword_filtered = [
                item for item in all_items 
                if keyword_exists_in_news(item, keyword)
            ]
            
            date_filtered = [
                item for item in keyword_filtered
                if is_within_date_range(item.get('pubDate', ''), start_dt, end_dt)
            ]
            
            print(f"  {keyword}: {len(all_items)}개 수집 → 키워드 {len(keyword_filtered)}개 → 전일 {len(date_filtered)}개")
            
            return date_filtered
        else:
            print(f"Error {response.status_code}: {keyword}")
            return []
    except Exception as e:
        print(f"Exception for {keyword}: {e}")
        return []

def remove_duplicates(all_news_by_keyword):
    """중복 제거 - 키워드 순서대로 우선순위 적용"""
    seen_links = set()
    seen_titles = set()
    deduplicated = defaultdict(list)
    
    for keyword in KEYWORDS:
        if keyword not in all_news_by_keyword:
            continue
            
        for news in all_news_by_keyword[keyword]:
            link = news['link']
            normalized_title = normalize_title(news['title'])
            
            if link in seen_links or normalized_title in seen_titles:
                continue
            
            seen_links.add(link)
            seen_titles.add(normalized_title)
            deduplicated[keyword].append(news)
    
    return deduplicated

def save_data(grouped_news_by_keyword, stats, yesterday_date):
    """데이터 저장 (JSON, Excel, Markdown)"""
    now = get_kst_now()
    timestamp = yesterday_date.replace("-", "")
    date_str = now.strftime("%Y-%m-%d %H:%M KST")
    
    # 디렉토리 생성
    Path(DATA_DIR).mkdir(exist_ok=True)
    Path(REPORTS_DIR).mkdir(exist_ok=True)
    
    # JSON 저장
    json_path = f"{DATA_DIR}/mvno_daily_{timestamp}.json"
    json_data = {
        "report_date": yesterday_date,
        "generated_at": date_str,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "statistics": stats,
        "news_by_keyword": grouped_news_by_keyword
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ JSON 저장: {json_path}")
    
    # Excel 저장
    excel_path = f"{REPORTS_DIR}/mvno_daily_{timestamp}.xlsx"
    excel_data = []
    
    for keyword in KEYWORDS:
        groups = grouped_news_by_keyword.get(keyword, [])
        for group in groups:
            representative = select_representative_title(group)
            excel_data.append({
                "키워드": keyword,
                "제목": clean_title(representative['title']),
                "링크": representative['link'],
                "발행일": representative['pubDate'],
                "유사기사수": len(group) - 1,
                "그룹크기": len(group)
            })
    
    if excel_data:
        df = pd.DataFrame(excel_data)
        df.to_excel(excel_path, index=False, engine='openpyxl')
        print(f"✓ Excel 저장: {excel_path}")
    
    # Markdown 저장
    md_path = f"{REPORTS_DIR}/mvno_daily_{timestamp}.md"
    md_content = f"# MVNO 일일 뉴스 요약\n\n"
    md_content += f"**보고 날짜**: {yesterday_date} (전일)\n"
    md_content += f"**생성 시간**: {date_str}\n"
    md_content += f"**총 뉴스**: {stats['total_news']}개\n\n"
    md_content += "---\n\n"
    
    for keyword in KEYWORDS:
        groups = grouped_news_by_keyword.get(keyword, [])
        if groups:
            total_in_keyword = sum(len(group) for group in groups)
            md_content += f"## 🔍 {keyword} ({total_in_keyword}개)\n\n"
            
            for idx, group in enumerate(groups, 1):
                representative = select_representative_title(group)
                title = clean_title(representative['title'])
                link = representative['link']
                pub_date = representative['pubDate']
                similar_count = len(group) - 1
                
                md_content += f"### {idx}. {title}\n"
                if similar_count > 0:
                    md_content += f"**유사 기사**: {similar_count}건\n"
                md_content += f"**링크**: {link}\n"
                md_content += f"**발행일**: {pub_date}\n\n"
                
                if similar_count > 0:
                    md_content += "**유사 기사 목록**:\n"
                    for similar_news in group[1:]:
                        similar_title = clean_title(similar_news['title'])
                        md_content += f"- {similar_title}\n"
                        md_content += f"  - {similar_news['link']}\n"
                    md_content += "\n"
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✓ Markdown 저장: {md_path}")
    
    return json_path, excel_path, md_path

def send_telegram_summary(stats, yesterday_date, file_paths):
    """텔레그램 요약 전송"""
    now = get_kst_now()
    today = now.strftime("%Y-%m-%d %H:%M KST")
    
    message = f"📊 <b>MVNO 일일 뉴스 요약</b>\n\n"
    message += f"📅 보고 날짜: {yesterday_date} (전일)\n"
    message += f"🕐 생성 시간: {today}\n"
    message += f"📰 총 기사: {stats['total_news']}개\n\n"
    
    if stats['total_news'] > 0:
        message += f"📈 <b>키워드별 통계</b>\n"
        for keyword, count in stats['by_keyword'].items():
            if count > 0:
                message += f"  • {keyword}: {count}개\n"
        message += "\n"
    
    message += f"💾 <b>저장 파일</b>\n"
    message += f"  • JSON: {file_paths['json']}\n"
    message += f"  • Excel: {file_paths['excel']}\n"
    message += f"  • Markdown: {file_paths['markdown']}\n"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        print(f"Telegram error: {e}")
        return None

def main():
    now = get_kst_now()
    start_dt, end_dt = get_yesterday_range()
    
    today = now.strftime("%Y-%m-%d %H:%M KST")
    yesterday_date = start_dt.strftime("%Y-%m-%d")
    
    print(f"Starting daily news summary at {today}...")
    print(f"Collection period: {yesterday_date} 00:00 ~ 23:59")
    print(f"Similarity threshold: {SIMILARITY_THRESHOLD}")
    
    # 1단계: 모든 키워드의 뉴스 수집
    all_news_by_keyword = {}
    
    for keyword in KEYWORDS:
        print(f"Searching: {keyword}")
        news_list = search_naver_news(keyword, start_dt, end_dt)
        all_news_by_keyword[keyword] = news_list
    
    # 2단계: 중복 제거
    print("\nRemoving duplicates...")
    deduplicated_news = remove_duplicates(all_news_by_keyword)
    
    # 3단계: 유사 제목 그룹화
    print("\nGrouping similar news...")
    grouped_news_by_keyword = {}
    stats = {
        'total_news': 0,
        'by_keyword': {}
    }
    
    for keyword, news_list in deduplicated_news.items():
        groups = group_similar_news(news_list)
        grouped_news_by_keyword[keyword] = groups
        
        total_articles = len(news_list)
        num_groups = len(groups)
        similar_count = sum(len(g) - 1 for g in groups if len(g) > 1)
        
        stats['total_news'] += total_articles
        stats['by_keyword'][keyword] = total_articles
        
        print(f"  {keyword}: {total_articles}개 → {num_groups}개 그룹 (유사 {similar_count}건)")
    
    print(f"\nTotal articles: {stats['total_news']}")
    
    # 뉴스가 없으면 종료
    if stats['total_news'] == 0:
        print("No articles found for yesterday. Exiting...")
        return
    
    # 4단계: 데이터 저장
    print("\nSaving data...")
    json_path, excel_path, md_path = save_data(grouped_news_by_keyword, stats, yesterday_date)
    
    # 5단계: 텔레그램 요약 전송
    print("\nSending Telegram summary...")
    file_paths = {
        'json': json_path,
        'excel': excel_path,
        'markdown': md_path
    }
    send_telegram_summary(stats, yesterday_date, file_paths)
    
    print("\n✅ Completed!")
    print(f"📊 Total: {stats['total_news']} articles")
    print(f"💾 Files saved in: {DATA_DIR}/, {REPORTS_DIR}/")

if __name__ == "__main__":
    main()
