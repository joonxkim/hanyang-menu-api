```python
import requests
from bs4 import BeautifulSoup
import datetime
from deep_translator import GoogleTranslator
import json
import re
import time

kst_time = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
monday = kst_time - datetime.timedelta(days=kst_time.weekday())

weekly_menu_data = {}
days_str = ["월", "화", "수", "목", "금", "토", "일"]

translator_en = GoogleTranslator(source='ko', target='en')
translator_zh = GoogleTranslator(source='ko', target='zh-CN')

headers = {
    "User-Agent": "Mozilla/5.0"
}

for i in range(7):

    target_date = monday + datetime.timedelta(days=i)

    date_str_url = target_date.strftime("%Y%%2F%m%%2F%d")
    date_key = target_date.strftime("%Y-%m-%d")

    url = f"https://www.hanyang.ac.kr/web/www/re13?p_p_id=kr_ac_hanyang_cafe_web_portlet_CafePortlet&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_sMenuDate={date_str_url}&_kr_ac_hanyang_cafe_web_portlet_CafePortlet_action=view"

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
    except Exception as e:
        print(date_key, e)
        weekly_menu_data[f"{date_key}({days_str[i]})"] = []
        continue

    daily_menu_data = []

    if response.status_code != 200:
        weekly_menu_data[f"{date_key}({days_str[i]})"] = []
        continue

    soup = BeautifulSoup(response.text, "html.parser")

    elements = soup.find_all(["h3", "p"])

    is_target_cafe = False
    current_meal = None
    lunch_count = 0

    for elem in elements:

        text = elem.get_text().strip()

        if not text:
            continue

        if elem.name == "h3":

            if "창의인재원" in text:
                is_target_cafe = True
                continue

            if is_target_cafe:

                if "조식" in text:
                    current_meal = "조식"

                elif "중식" in text:
                    current_meal = "중식"
                    lunch_count = 0

                elif "석식" in text:
                    current_meal = "석식"

                elif "hyu-element" in elem.get("class", []):
                    break

        elif elem.name == "p" and is_target_cafe and current_meal:

            menu_text = text

            if "사용자별 바로가기" in menu_text:
                continue

            parts = menu_text.split('"')

            if len(parts) >= 3:

                prefix = parts[0].strip()
                main_mixed = parts[1].strip()
                side_dishes = parts[2].strip()

                eng_match = re.search(r"[a-zA-Z]", main_mixed)

                if eng_match:
                    idx = eng_match.start()
                    kor_main = main_mixed[:idx].strip()
                    eng_main = main_mixed[idx:].strip()
                else:
                    kor_main = main_mixed
                    eng_main = ""

                kor_full = f"{prefix} {kor_main} {side_dishes}".strip()

            else:

                kor_full = menu_text
                eng_main = ""
                side_dishes = ""

            eng_full = ""

            if eng_main:
                eng_full += eng_main

            if side_dishes:

                try:
                    time.sleep(0.3)
                    eng_side = translator_en.translate(side_dishes)

                    if eng_full:
                        eng_full += ", "

                    eng_full += eng_side

                except Exception as e:
                    print(date_key, "ENG", e)

            chn_full = ""

            try:
                time.sleep(0.3)
                chn_full = translator_zh.translate(kor_full)

            except Exception as e:
                print(date_key, "CHN", e)
                chn_full = kor_full

            parsed_menu = {
                "type": current_meal,
                "kor": kor_full,
                "eng": eng_full,
                "chn": chn_full
            }

            daily_menu_data.append(parsed_menu)

            if current_meal == "조식":
                current_meal = None

            elif current_meal == "중식":
                lunch_count += 1
                if lunch_count >= 2:
                    current_meal = None

            elif current_meal == "석식":
                current_meal = None

    weekly_menu_data[f"{date_key}({days_str[i]})"] = daily_menu_data

    print(date_key, "완료")

    time.sleep(1)

with open(
    "weekly_menu.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        weekly_menu_data,
        f,
        ensure_ascii=False,
        indent=4
    )

print("weekly_menu.json 생성 완료")
```
