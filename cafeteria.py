import requests
from bs4 import BeautifulSoup
import datetime
from deep_translator import GoogleTranslator
import json
import re
import time 

# 1. 한국 시간 기준 '이번 주 월요일' 날짜 찾기
kst_time = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
monday = kst_time - datetime.timedelta(days=kst_time.weekday())

weekly_menu_data = {}
days_str = ["월", "화", "수", "목", "금", "토", "일"]

# 번역기 준비
translator_en = GoogleTranslator(source='ko', target='en')
translator_zh = GoogleTranslator(source='ko', target='zh-CN')

for i in range(7):
    target_date = monday + datetime.timedelta(days=i)
    date_str_url = target_date.strftime("%Y%%2F%m%%2F%d") 
    date_key = target_date.strftime("%Y-%m-%d") 
    
    url = f"https://www.hanyang.ac.kr/web/www/re13?p_p_id=kr_ac_hanyang_cafe_web_portlet_CafePortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_sMenuDate={date_str_url}&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_action=view"
    
    try:
        response = requests.get(url, timeout=10)
    except:
        print(f"{date_key} 데이터를 가져오는 데 지연이 발생해 건너뜁니다.")
        continue 
        
    daily_menu_data = [] 
    
    if response.status_code == 200:
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
                
                # 💡 [버그 해결 핵심 방어선] 
                # 식단이 아니라 단순 공지/안내 문구라면 브레이크를 터트리지 않고 그냥 다음 줄로 패스(continue)합니다!
                if any(k in menu_text for k in ["운영시간", "안내사항", "공지", "휴무", "미운영", "바로가기"]):
                    continue
                    
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
                        try: eng_sides = translator_en.translate(side_dishes)
                        except: eng_sides = ""
                    
                    kor_full = f"{prefix} {kor_main} {side_dishes}".strip()
                    eng_full = f"{eng_main}, {eng_sides}".strip() if eng_main else eng_sides
                    
                    try: chn_full = translator_zh.translate(kor_full)
                    except: chn_full = ""
                    
                    parsed_menu = {"type": current_meal, "kor": kor_full, "eng": eng_full, "chn": chn_full}
                else:
                    # 따옴표가 없는 일반 메뉴 형태일 때 (안내문이 아닌 최소 3글자 이상의 진짜 메뉴만 인정)
                    if len(menu_text) > 3:
                        try: chn_fallback = translator_zh.translate(menu_text)
                        except: chn_fallback = ""
                        parsed_menu = {"type": current_meal, "kor": menu_text, "eng": "", "chn": chn_fallback}
                    else:
                        continue 

                # 진짜 메뉴 데이터가 확보되었을 때만 개수를 세고 제한을 적용합니다!
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

    weekly_menu_data[f"{date_key}({days_str[i]})"] = daily_menu_data
    time.sleep(0.5)

with open('weekly_menu.json', 'w', encoding='utf-8') as f:
    json.dump(weekly_menu_data, f, ensure_ascii=False, indent=4)
    
print("weekly_menu.json 파일이 성공적으로 생성되었습니다!")
