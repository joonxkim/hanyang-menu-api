import requests
from bs4 import BeautifulSoup
import datetime
from deep_translator import GoogleTranslator
import json
import re
import time
import os

# ---------------------------------------------------------
# [설정] 날짜 및 기본 정보 세팅
# ---------------------------------------------------------
kst_time = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
monday = kst_time - datetime.timedelta(days=kst_time.weekday())
days_str = ["월", "화", "수", "목", "금", "토", "일"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# ---------------------------------------------------------
# [사전 준비 1] 커스텀 번역 사전 (food_dict.json) 로드 및 자동 생성
# ---------------------------------------------------------
dict_file = 'food_dict.json'
if not os.path.exists(dict_file):
    # 번역기가 못 잡는 고유명사나 발음 기호 초기 세팅 (언제든 깃허브에서 직접 추가 가능!)
    default_dict = {
        "설렁탕": {"en": "Seolleongtang", "zh-CN": "雪浓汤(Seolleongtang)"},
        "깍두기": {"en": "Kkakdugi", "zh-CN": "萝卜块(Kkakdugi)"},
        "돈카츠동": {"en": "Tonkatsu Donburi", "zh-CN": "炸猪排丼"}
    }
    with open(dict_file, 'w', encoding='utf-8') as f:
        json.dump(default_dict, f, ensure_ascii=False, indent=4)

with open(dict_file, 'r', encoding='utf-8') as f:
    food_dict = json.load(f)

# ---------------------------------------------------------
# [사전 준비 2] 하드코어 식재료 태그 사전 (tag_rules.json) 로드 및 자동 생성
# ---------------------------------------------------------
tag_file = 'tag_rules.json'
if not os.path.exists(tag_file):
    default_tags = {
        "🐷 돼지고기(Pork/猪肉)": ["돼지", "돈", "제육", "삼겹", "햄", "소시지", "베이컨", "순대", "탕수육", "돈까스", "카츠"],
        "🐄 소고기(Beef/牛肉)": ["소고기", "우육", "불고기", "차돌", "설렁탕", "갈비", "함박", "우삼겹", "규동"],
        "🐔 닭고기(Chicken/鸡肉)": ["닭", "치킨", "가라아게", "찜닭", "깐풍기", "닭갈비", "스리라차치킨"],
        "🐟 해산물(Seafood/海鲜)": ["오징어", "새우", "생선", "참치", "멸치", "꽁치", "고등어", "연어", "어묵", "명태", "쭈꾸미", "게맛살", "다시마"],
        "🥚 계란(Egg/鸡蛋)": ["계란", "달걀", "후라이", "오므라이스", "지단", "메추리알"],
        "🥛 유제품(Dairy/乳制品)": ["우유", "치즈", "요구르트", "크림", "버터"],
        "🥜 콩/견과(Soy&Nuts/大豆&坚果)": ["땅콩", "아몬드", "호두", "두부", "콩나물", "비지", "콩가루"],
        "🌾 밀가루(Wheat/小麦)": ["면", "소면", "라면", "우동", "스파게티", "파스타", "빵", "샌드위치", "튀김", "만두"]
    }
    with open(tag_file, 'w', encoding='utf-8') as f:
        json.dump(default_tags, f, ensure_ascii=False, indent=4)

with open(tag_file, 'r', encoding='utf-8') as f:
    tag_rules = json.load(f)

# 태그 추출을 위한 판독기 함수
def extract_tags(menu_text):
    if not menu_text: return []
    tags = set()
    for tag_name, keywords in tag_rules.items():
        for keyword in keywords:
            if keyword in menu_text:
                tags.add(tag_name)
                break # 한 카테고리에서 하나라도 발견되면 더 이상 검사 안 함
    return list(tags)

# ---------------------------------------------------------
# [1단계] 주간 메뉴 크롤링 및 가로->세로 파싱
# ---------------------------------------------------------
# 요일별 빈 리스트 생성 (예: "2026-06-08(월)": [])
crawled_data = {}
day_keys = []
for i in range(7):
    day_key = f"{(monday + datetime.timedelta(days=i)).strftime('%Y-%m-%d')}({days_str[i]})"
    crawled_data[day_key] = []
    day_keys.append(day_key)

print("🔍 한양대 학식 주간 식단표 단일 크롤링을 시도합니다...")

weekly_url = "https://www.hanyang.ac.kr/web/www/re13?p_p_id=kr_ac_hanyang_cafe_web_portlet_CafePortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_action=view"

try:
    response = requests.get(weekly_url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 조식, 중식, 석식을 담고 있는 블록들 찾기
    meal_blocks = soup.find_all('div', class_='hyu-list-body-item')
    
    for block in meal_blocks:
        cols = block.find_all('div', class_='hyu-list-body-item-col')
        if not cols or len(cols) < 8: continue # 타이틀 1칸 + 월~일 7칸 = 총 8칸
        
        # 첫 번째 칸에서 '조식', '중식', '석식' 추출
        meal_type_tag = cols[0].find('h4')
        if not meal_type_tag: continue
        current_meal = meal_type_tag.get_text().strip()
        
        # 가로 데이터를 세로(요일별) 데이터로 매핑
        for day_idx in range(7):
            col_idx = day_idx + 1 # 월요일은 1번 인덱스, 화요일은 2번 인덱스...
            day_col = cols[col_idx]
            menu_ps = day_col.find_all('p')
            
            for p_tag in menu_ps:
                menu_text = p_tag.get_text().strip()
                if not menu_text or "사용자별 바로가기" in menu_text: continue
                
                # 따옴표(") 기준으로 분리
                parts = menu_text.split('"')
                if len(parts) >= 3:
                    prefix = parts[0].strip()       
                    main_mixed = parts[1].strip()   
                    side_dishes = parts[2].strip()  
                    
                    eng_match = re.search(r'[a-zA-Z]', main_mixed)
                    if eng_match:
                        idx = eng_match.start()
                        kor_main = main_mixed[:idx].strip()  
                        eng_main = main_mixed[idx:].strip()  
                    else:
                        kor_main = main_mixed
                        eng_main = ""
                    
                    parsed_menu = {
                        "type": current_meal, 
                        "prefix": prefix, 
                        "kor_main": kor_main, 
                        "eng_main": eng_main, 
                        "side_dishes": side_dishes,
                        "raw_text": None
                    }
                else:
                    parsed_menu = {"type": current_meal, "raw_text": menu_text} if len(menu_text) > 5 else None

                if parsed_menu:
                    # 해당 요일의 주머니에 메뉴 넣기!
                    crawled_data[day_keys[day_idx]].append(parsed_menu)

except Exception as e:
    print(f"🚨 크롤링 에러 발생: {e}")

# ---------------------------------------------------------
# [2단계] 스마트 구글 번역 & 식재료 태그 분석 단계
# ---------------------------------------------------------
print("✅ 크롤링 및 파싱 완료. 스마트 번역 및 식재료 태그 분석을 개시합니다...")

translator_en = GoogleTranslator(source='ko', target='en')
translator_zh = GoogleTranslator(source='ko', target='zh-CN')

def smart_translate(text, target_lang):
    if not text: return ""
    translator = translator_en if target_lang == 'en' else translator_zh
    
    # 1. 번역 전 가로채기 (커스텀 사전에 있는 단어 미리 치환)
    for ko_word, trans_dict in food_dict.items():
        if ko_word in text and target_lang in trans_dict:
            text = text.replace(ko_word, trans_dict[target_lang])
            
    # 2. 번역 실행
    try:
        translated = translator.translate(text)
        time.sleep(0.5) # 트래픽 제한 우회
        return translated
    except Exception as e:
        print(f"🚨 {target_lang} 번역 실패: {e}")
        return text 

final_weekly_menu = {}

for day_key, menus in crawled_data.items():
    final_daily = []
    
    for temp_menu in menus:
        m_type = temp_menu["type"]
        
        if temp_menu.get("raw_text"):
            kor_full = temp_menu["raw_text"]
            eng_full = smart_translate(kor_full, 'en')
            chn_full = smart_translate(kor_full, 'zh-CN')
        else:
            kor_full = f"{temp_menu['prefix']} {temp_menu['kor_main']} {temp_menu['side_dishes']}".strip()
            
            # 영어는 반찬만 번역 후 메인 메뉴 영어 이름과 합치기
            eng_sides = smart_translate(temp_menu["side_dishes"], 'en')
            eng_full = f"{temp_menu['eng_main']}, {eng_sides}".strip() if temp_menu['eng_main'] else eng_sides

            # 중국어는 전체 문장 번역
            chn_full = smart_translate(kor_full, 'zh-CN')
        
        # 💡 [핵심] 조립된 한국어 메뉴 텍스트를 기반으로 식재료 태그 자동 추출
        menu_tags = extract_tags(kor_full)
        
        final_daily.append({
            "type": m_type,
            "kor": kor_full,
            "eng": eng_full,
            "chn": chn_full,
            "tags": menu_tags # 추출된 태그 배열을 최종 데이터에 추가!
        })
        
    final_weekly_menu[day_key] = final_daily

# ---------------------------------------------------------
# [3단계] JSON 저장 단계
# ---------------------------------------------------------
with open('weekly_menu.json', 'w', encoding='utf-8') as f:
    json.dump(final_weekly_menu, f, ensure_ascii=False, indent=4)
    
print("🎉 weekly_menu.json 파일이 완벽하게 생성되었습니다! (태그 기능 포함)")
