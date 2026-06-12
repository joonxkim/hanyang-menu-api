import requests
from bs4 import BeautifulSoup
import json
import re

# 1. 설정 및 기본 정보
board_url = "https://hydorm.hanyang.ac.kr/service/board/notice/a/all//index.do"
# 게시글로 바로가는 기본 URL 형태 (고유 번호를 뒤에 붙여서 완성합니다)
base_view_url = "https://hydorm.hanyang.ac.kr/service/board/notice/view.do?bdSeq="

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

print("🔍 기숙사 공지사항 크롤링을 시작합니다...")

notice_data = []

try:
    response = requests.get(board_url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 2. '공지' 마크가 붙은 고정 게시글(tr class="notice")만 모두 찾기
    notice_rows = soup.find_all('tr', class_='notice')
    
    # 3. 최신 3개만 추출
    for row in notice_rows[:3]:
        # 날짜 추출 (보통 마지막 td 요소에 있음)
        tds = row.find_all('td')
        if not tds: continue
        date = tds[-1].get_text().strip()
        
        # 제목 및 링크 고유 번호 추출
        a_tag = row.find('a')
        if not a_tag: continue
        
        title = a_tag.get('title', a_tag.get_text().strip()).strip()
        onclick_text = a_tag.get('onclick', '')
        
        # 정규식을 이용해 onclick="return self.view('3525');" 에서 숫자(3525)만 뽑아내기
        seq_match = re.search(r"view\('(\d+)'\)", onclick_text)
        if seq_match:
            seq_id = seq_match.group(1)
            full_link = f"{base_view_url}{seq_id}"
        else:
            full_link = board_url # 번호를 못 찾으면 전체 게시판 링크로 대체 (안전장치)
            
        notice_data.append({
            "title": title,
            "date": date,
            "url": full_link
        })

except Exception as e:
    print(f"🚨 공지사항 크롤링 에러 발생: {e}")

# 4. JSON 파일로 저장 (식단표와 완벽히 분리된 notice.json)
with open('notice.json', 'w', encoding='utf-8') as f:
    json.dump(notice_data, f, ensure_ascii=False, indent=4)

print(f"🎉 notice.json 파일 생성 완료! (총 {len(notice_data)}개의 공지사항)")
