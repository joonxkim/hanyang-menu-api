import requests
from bs4 import BeautifulSoup
import datetime
from deep_translator import GoogleTranslator
import json
import re

# 1. 깃허브 서버는 UTC 기준이므로 한국 시간(KST, UTC+9)으로 맞춰줍니다.
kst_time = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
date_str = kst_time.strftime("%Y%%2F%m%%2F%d") 

url = f"https://www.hanyang.ac.kr/web/www/re13?p_p_id=kr_ac_hanyang_cafe_web_portlet_CafePortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_sMenuDate={date_str}&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_action=view"

response = requests.get(url)

# 결과를 담을 빈 리스트 생성
menu_data = []

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    meal_titles = soup.find_all('h3', class_='hyu-element')
    
    for title in meal_titles:
        title_text = title.get_text().strip()
        
        if "조식" in title_text or "중식" in title_text or "석식" in title_text:
            menu_element = title.find_next('p')
            
            if menu_element:
                menu_text = menu_element.get_text().strip()
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
                    
                    # 딕셔너리 형태로 리스트에 추가
                    menu_data.append({
                        "type": title_text,
                        "kor": kor_full,
                        "eng": eng_full
                    })
                else:
                    menu_data.append({
                        "type": title_text,
                        "kor": menu_text,
                        "eng": ""
                    })

# 2. 완성된 데이터를 menu.json 파일로 저장 (한글 깨짐 방지 utf-8 설정)
with open('menu.json', 'w', encoding='utf-8') as f:
    json.dump(menu_data, f, ensure_ascii=False, indent=4)
    
print("menu.json 파일이 성공적으로 생성되었습니다!")