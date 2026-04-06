import requests
from bs4 import BeautifulSoup
import datetime
from deep_translator import GoogleTranslator
import json
import re

# 1. 한국 시간 설정
kst_time = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
date_str = kst_time.strftime("%Y%%2F%m%%2F%d") 

url = f"https://www.hanyang.ac.kr/web/www/re13?p_p_id=kr_ac_hanyang_cafe_web_portlet_CafePortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_sMenuDate={date_str}&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_action=view"

response = requests.get(url)
menu_data = []

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    elements = soup.find_all(['h3', 'p'])
    
    is_target_cafe = False
    current_meal = None
    lunch_count = 0
    
    for elem in elements:
        text = elem.get_text().strip()
        if not text: continue
        
        # 1. 식당 및 끼니(h3) 확인
        if elem.name == 'h3':
            if "창의인재원" in text:
                is_target_cafe = True
                continue
                
            if is_target_cafe:
                if "조식" in text:
                    current_meal = "조식"
                elif "중식" in text:
                    current_meal = "중식"
                    lunch_count = 0 # 중식 카운트 리셋
                elif "석식" in text:
                    current_meal = "석식"
                elif 'hyu-element' in elem.get('class', []):
                    # 창의인재원식당 구역을 완전히 벗어남
                    break
                    
        # 2. 제안해주신 개수 제한 논리 적용 (p)
        elif elem.name == 'p' and is_target_cafe and current_meal:
            menu_text = text
            if "사용자별 바로가기" in menu_text:
                continue
                
            # --- 메뉴 텍스트 가공 및 번역 ---
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
                
                eng_sides = ""
                if side_dishes:
                    try:
                        eng_sides = GoogleTranslator(source='ko', target='en').translate(side_dishes)
                    except:
                        eng_sides = "(Translation failed)"
                
                kor_full = f"{prefix} {kor_main} {side_dishes}".strip()
                eng_full = f"{eng_main}, {eng_sides}".strip() if eng_main else eng_sides
                
                parsed_menu = {"type": current_meal, "kor": kor_full, "eng": eng_full}
            else:
                parsed_menu = {"type": current_meal, "kor": menu_text, "eng": ""} if len(menu_text) > 5 else None

            # --- 💡 핵심: 제안하신 '개수 제한 브레이크' 로직 ---
            if parsed_menu:
                if current_meal == "조식":
                    menu_data.append(parsed_menu)
                    current_meal = None  # 1개 담았으니 문 닫음! (다음 p 무시)
                    
                elif current_meal == "중식":
                    menu_data.append(parsed_menu)
                    lunch_count += 1
                    if lunch_count >= 2:
                        current_meal = None  # 2개 담았으니 문 닫음!
                        
                elif current_meal == "석식":
                    menu_data.append(parsed_menu)
                    # 석식 1개 담았으면 더 볼 것 없이 파싱 자체를 완전히 종료!
                    break

with open('menu.json', 'w', encoding='utf-8') as f:
    json.dump(menu_data, f, ensure_ascii=False, indent=4)
    
print("menu.json 파일이 성공적으로 생성되었습니다!")
