import requests
from bs4 import BeautifulSoup
import datetime
from deep_translator import GoogleTranslator
import json
import re

# 1. 한국 시간(KST) 설정
kst_time = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
date_str = kst_time.strftime("%Y%%2F%m%%2F%d") 

url = f"https://www.hanyang.ac.kr/web/www/re13?p_p_id=kr_ac_hanyang_cafe_web_portlet_CafePortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_sMenuDate={date_str}&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_action=view"

response = requests.get(url)
menu_data = []

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    meal_titles = soup.find_all('h3', class_='hyu-element')
    
    for title in meal_titles:
        title_text = title.get_text().strip()
        
        if "조식" in title_text or "중식" in title_text or "석식" in title_text:
            
            # 💡 핵심 변경 부분: 현재 <h3> 이름표 이후에 나오는 모든 태그를 하나씩 뒤져봅니다.
            for next_elem in title.find_all_next():
                
                # 다음 <h3> 이름표를 만나면 (예: 중식 메뉴 찾다가 석식 이름표를 만나면) 탐색 중단!
                if next_elem.name == 'h3' and 'hyu-element' in next_elem.get('class', []):
                    break
                    
                # <p> 태그를 찾으면 메뉴로 인식해서 가져오기
                if next_elem.name == 'p':
                    menu_text = next_elem.get_text().strip()
                    
                    # 내용이 비어있지 않은 진짜 메뉴일 때만 처리
                    if menu_text:
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
                            
                            # 완성된 데이터를 리스트에 추가 (중식이 여러 개면 배열에 여러 개가 들어갑니다)
                            menu_data.append({
                                "type": title_text,
                                "kor": kor_full,
                                "eng": eng_full
                            })
                        else:
                            # 큰따옴표가 없는 예외적인 메뉴일 경우
                            menu_data.append({
                                "type": title_text,
                                "kor": menu_text,
                                "eng": ""
                            })

# 2. 완성된 데이터를 menu.json 파일로 저장
with open('menu.json', 'w', encoding='utf-8') as f:
    json.dump(menu_data, f, ensure_ascii=False, indent=4)
    
print("menu.json 파일이 성공적으로 생성되었습니다!")
