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
    
    # 1. 전체 페이지에서 '창의인재원' 식당의 이름표(h3)를 제일 먼저 콕 집어 찾습니다.
    target_h3 = None
    for h3 in soup.find_all('h3', class_='hyu-element'):
        if "창의인재원" in h3.get_text():
            target_h3 = h3
            break

    # 창의인재원식당을 찾았다면, 딱 그 밑에서부터만 탐색을 시작합니다!
    if target_h3:
        current_meal = None
        
        # target_h3 바로 다음부터 나오는 태그들을 순서대로 확인
        for elem in target_h3.find_all_next(['h3', 'p']):
            
            if elem.name == 'h3':
                # hyu-element 클래스가 있는 진짜 이름표만 취급
                if 'hyu-element' in elem.get('class', []):
                    text = elem.get_text().strip()
                    
                    if "조식" in text or "중식" in text or "석식" in text:
                        current_meal = text
                    elif "창의인재원" not in text:
                        # 💡 핵심 방어선(Break): 창의인재원이 아닌 '다른 식당 이름표(예: 학생식당)'가 
                        # 등장하는 순간, 더 이상 볼 필요 없이 탐색을 완전히 강제 종료합니다!
                        break
                        
            elif elem.name == 'p' and current_meal:
                menu_text = elem.get_text().strip()
                
                # 빈칸이 아니고 실제 메뉴 텍스트일 때만 처리
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
                            "type": current_meal,
                            "kor": kor_full,
                            "eng": eng_full
                        })
                    else:
                        # 혹시 모를 쓰레기값이 들어가는 것을 방지하기 위해 최소 길이 제한
                        if len(menu_text) > 5:
                            menu_data.append({
                                "type": current_meal,
                                "kor": menu_text,
                                "eng": ""
                            })

with open('menu.json', 'w', encoding='utf-8') as f:
    json.dump(menu_data, f, ensure_ascii=False, indent=4)
    
print("menu.json 파일이 성공적으로 생성되었습니다!")
