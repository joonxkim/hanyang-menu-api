import requests
from bs4 import BeautifulSoup
import datetime
from deep_translator import GoogleTranslator
import json
import re

kst_time = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
date_str = kst_time.strftime("%Y%%2F%m%%2F%d") 

url = f"https://www.hanyang.ac.kr/web/www/re13?p_p_id=kr_ac_hanyang_cafe_web_portlet_CafePortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_sMenuDate={date_str}&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_action=view"

response = requests.get(url)
menu_data = []

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    elements = soup.find_all(['h3', 'p'])
    
    current_cafe = ""
    current_meal = None
    
    for elem in elements:
        if elem.name == 'h3':
            text = elem.get_text().strip()
            if not text: continue
            
            if "조식" in text or "중식" in text or "석식" in text:
                current_meal = text 
            elif "댓글" not in text and "바로가기" not in text:
                current_cafe = text 
                current_meal = None 
                
        # 💡 핵심: 메뉴(p)를 발견했을 때, 현재 식당이 '창의인재원'일 때만 저장합니다!
        elif elem.name == 'p' and current_meal:
            if "창의인재원" in current_cafe:
                menu_text = elem.get_text().strip()
                
                if menu_text and "사용자별 바로가기" not in menu_text:
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
                        
                        menu_data.append({
                            "type": current_meal, # 깔끔하게 '조식', '중식', '석식'만 들어갑니다
                            "kor": kor_full,
                            "eng": eng_full
                        })
                    else:
                        menu_data.append({
                            "type": current_meal,
                            "kor": menu_text,
                            "eng": ""
                        })

with open('menu.json', 'w', encoding='utf-8') as f:
    json.dump(menu_data, f, ensure_ascii=False, indent=4)
    
print("menu.json 파일이 성공적으로 생성되었습니다!")
