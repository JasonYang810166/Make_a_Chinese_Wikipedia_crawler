import time
import requests
from bs4 import BeautifulSoup

# 起始頁（Wikipedia 中文首頁 Portal）
START_URL = "https://zh.wikipedia.org/wiki/Portal:%E9%A6%96%E9%A0%81"
# 基本網址（用來還原 /wiki/xxxx 相對連結）
BASE = "https://zh.wikipedia.org"
# 最多要抓的頁數
MAX_PAGES = 300
# 每次請求間隔秒數，避免過快觸發 Wikipedia 的防爬蟲規則
SLEEP = 1.0

# 瀏覽器 headers（User-Agent 不能省，Wikipedia 會擋掉 requests 預設 UA）
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 檢查 response 是否為 HTML 頁面
def is_html(resp):
    ctype = resp.headers.get("Content-Type", "").lower()
    return resp.status_code == 200 and "text/html" in ctype

# 建立 session，重用連線，提高效率
session = requests.Session()
session.headers.update(HEADERS)

visited = set()  # 用來記錄已經抓過的網址，避免重複
count = 0        # 計數器，記錄已經抓取的頁數

with open("Wiki.txt", "w", encoding="utf-8") as file:
    # 抓取 Wikipedia 首頁
    res = session.get(START_URL, timeout=15)
    if not is_html(res):  # 若不是 HTML 直接中斷
        raise RuntimeError(f"起始頁非 HTML 或被擋：{res.status_code} {res.headers.get('Content-Type')}")

    # 用 BeautifulSoup 解析首頁 HTML
    soup = BeautifulSoup(res.content, "html.parser")

    # 找出首頁中 <td valign="top"> 的區塊（通常裡面有各種入口連結）
    td_tags = soup.find_all("td", {"valign": "top"})
    stop = False  # 用來控制是否提前停止（達到 MAX_PAGES）

    for td in td_tags:
        a_tags = td.find_all("a", href=True)  # 找出區塊中所有的超連結 <a href=...>

        for a in a_tags:
            href = a["href"]

            # 判斷連結格式，還原成完整網址
            if href.startswith("http"):
                full_url = href
            elif href.startswith("/"):
                full_url = BASE + href
            else:
                # 跳過其他形式（例如錨點 # 或 javascript:）
                continue

            # 如果已經抓過，跳過
            if full_url in visited:
                continue
            visited.add(full_url)

            # 抓取子頁面
            try:
                time.sleep(SLEEP)  # 加延遲，避免請求過快
                res2 = session.get(full_url, timeout=20)
                if not is_html(res2):  # 不是 HTML 頁面就跳過
                    continue

                # 解析子頁面 HTML
                soup2 = BeautifulSoup(res2.content, "html.parser")
                # 抓出所有段落文字 <p>
                paragraphs = soup2.find_all("p")
                if not paragraphs:
                    continue

                # 把所有段落文字接成一個字串
                main_content = "\n".join(p.get_text() for p in paragraphs)

                # 寫入檔案：網址 + 正文 + 分隔線
                file.write(full_url + "\n")
                file.write(main_content + "\n")
                file.write("---------------------------------------------------------------\n")

                count += 1
                if count >= MAX_PAGES:  # 若達到目標頁數就停止
                    stop = True
                    break

            except requests.RequestException:
                # 如果遇到網路錯誤（連線 timeout 等），就直接跳過該頁
                continue

        if stop:
            break

print(f"完成抓取 {count} 頁，輸出到 Wiki.txt")