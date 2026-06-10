import requests
from bs4 import BeautifulSoup
import datetime
from deep_translator import GoogleTranslator
import json
import re
import time 

kst_time = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
monday = kst_time - datetime.timedelta(days=kst_time.weekday())

days_str = ["월", "화", "수", "목", "금", "토", "일"]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ---------------------------------------------------------
# [1단계] 크롤링 단계
# ---------------------------------------------------------
crawled_data = {}

for i in range(7):
    target_date = monday + datetime.timedelta(days=i)
    date_str_url = target_date.strftime("%Y%%2F%m%%2F%d") 
    date_key = target_date.strftime("%Y-%m-%d") 
    full_key = f"{date_key}({days_str[i]})"
    
    url = f"https://www.hanyang.ac.kr/web/www/re13?p_p_id=kr_ac_hanyang_cafe_web_portlet_CafePortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_sMenuDate={date_str_url}&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_action=view"
    
    response = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                break 
        except Exception as e:
            print(f"[{full_key}] ⚠️ 연결 지연... 2초 후 재시도.")
            time.sleep(2)
            
    if response is None or response.status_code != 200:
        crawled_data[full_key] = []
        continue
        
    daily_menu_data = [] 
    soup = BeautifulSoup(response.text, 'html.parser')
    elements = soup.find_all(['h3', 'p'])
    
    is_target_cafe = False
    current_meal = None
    lunch_count = 0
    
    for elem in elements:
        text = elem.get_text().strip()
        if not text: continue
        
        if elem.name == 'h3':
            if "창의인재원" in text:
                is_target_cafe = True
                continue
                
            if is_target_cafe:
                if "조식" in text: current_meal = "조식"
                elif "중식" in text:
                    current_meal = "중식"
                    lunch_count = 0 
                elif "석식" in text: current_meal = "석식"
                elif 'hyu-element' in elem.get('class', []): break
                    
        elif elem.name == 'p' and is_target_cafe and current_meal:
            menu_text = text
            if "사용자별 바로가기" in menu_text: continue
                
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
                if current_meal == "조식":
                    daily_menu_data.append(parsed_menu)
                    current_meal = None 
                elif current_meal == "중식":
                    daily_menu_data.append(parsed_menu)
                    lunch_count += 1
                    if lunch_count >= 2: current_meal = None
                elif current_meal == "석식":
                    daily_menu_data.append(parsed_menu)
                    break

    crawled_data[full_key] = daily_menu_data
    time.sleep(1.5)

# ---------------------------------------------------------
# [2단계] 번역 단계 (메인 메뉴와 반찬을 분리해서 번역)
# ---------------------------------------------------------
print("✅ 크롤링 성공. 구글 번역을 개시합니다...")

translator_en = GoogleTranslator(source='ko', target='en')
translator_zh = GoogleTranslator(source='ko', target='zh-CN')

final_weekly_menu = {}

for day_key, menus in crawled_data.items():
    final_daily = []
    
    for temp_menu in menus:
        m_type = temp_menu["type"]
        
        # 큰따옴표 없는 예외 메뉴 (통째로 번역)
        if temp_menu.get("raw_text"):
            kor_full = temp_menu["raw_text"]
            eng_full = ""
            try:
                chn_full = translator_zh.translate(kor_full)
                time.sleep(0.4)
            except:
                chn_full = kor_full
                
        # 정상적인 메뉴 
        else:
            kor_full = f"{temp_menu['prefix']} {temp_menu['kor_main']} {temp_menu['side_dishes']}".strip()
            
            # 1. 영어 반찬 번역
            eng_sides = ""
            if temp_menu["side_dishes"]:
                try: 
                    eng_sides = translator_en.translate(temp_menu["side_dishes"])
                    time.sleep(0.4) 
                except: 
                    eng_sides = "(Translation failed)"
            
            eng_full = f"{temp_menu['eng_main']}, {eng_sides}".strip() if temp_menu['eng_main'] else eng_sides

            # 2. 중국어 메인 메뉴 번역 (독립)
            chn_main = ""
            if temp_menu["kor_main"]:
                try:
                    chn_main = translator_zh.translate(temp_menu["kor_main"])
                    time.sleep(0.4)
                except:
                    chn_main = temp_menu["kor_main"]

            # 3. 중국어 반찬 번역 (독립)
            chn_sides = ""
            if temp_menu["side_dishes"]:
                try:
                    chn_sides = translator_zh.translate(temp_menu["side_dishes"])
                    time.sleep(0.4)
                except:
                    chn_sides = temp_menu["side_dishes"]

            # 분리 번역된 결과를 다시 하나로 깔끔하게 조립
            prefix_str = temp_menu["prefix"] + " " if temp_menu["prefix"] else ""
            chn_full = f"{prefix_str}{chn_main} {chn_sides}".strip()
        
        final_daily.append({
            "type": m_type,
            "kor": kor_full,
            "eng": eng_full,
            "chn": chn_full
        })
        
    final_weekly_menu[day_key] = final_daily

# ---------------------------------------------------------
# [3단계] JSON 저장 단계
# ---------------------------------------------------------
with open('weekly_menu.json', 'w', encoding='utf-8') as f:
    json.dump(final_weekly_menu, f, ensure_ascii=False, indent=4)
    
print("🎉 weekly_menu.json 파일 생성 완료!")
