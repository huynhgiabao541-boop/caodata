import re

import scrapy
from scrapy import FormRequest

ATTACH_RE = re.compile(r"\.(pdf|docx?|xlsx?|zip|rar)(\?.*)?$", re.I)
def classify(title: str) -> str:
    """Phân loại thông báo theo tiêu đề để dễ so sánh/thống kê sau này."""
    t = title.lower()
    if "tiếp nhận đơn" in t:
        return "tiep_nhan_don_bao_ho"
    if "cấp bằng" in t:
        return "cap_bang_bao_ho"
    if "phục hồi hiệu lực" in t:
        return "phuc_hoi_hieu_luc"
    if "sửa đổi, bổ sung" in t:
        return "sua_doi_bo_sung_don"
    return "khac"


class PpdGiongCayTrongSpider(scrapy.Spider):
    name = "ppd_giong_cay_trong"
    allowed_domains = ["ppd.gov.vn"]
    start_urls = ["https://www.ppd.gov.vn/giong-cay-trong.html"]

    max_pages = 10  # giới hạn số trang cần cào

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 1.5,
        "AUTOTHROTTLE_ENABLED": True,
        "FEEDS": {"giong_cay_trong.json": {"format": "json", "encoding": "utf8", "overwrite": True}},
    }

    def parse(self, response, page=1):
        # Lấy các thẻ a trỏ tới bài viết chi tiết (thường nằm trong thư mục /tin-moi-nhat... hoặc có tiêu đề dài)
        for a in response.xpath("//a[contains(@href, '.html')]"):
            href = a.xpath("@href").get()
            title = a.xpath("normalize-space()").get("").strip()
            
            # Bỏ qua các link ngắn (menu) hoặc không chứa text
            if not href or len(title) < 20:
                continue
            
            # Dấu hiệu nhận biết link bài viết: URL thường chứa các từ khóa sau
            if 'tin-moi-nhat' not in href and 'quyet-dinh' not in href and 'thong-bao' not in href:
                continue

            # Tìm text chứa ngày tháng liền kề sau thẻ a (có thể có hoặc không)
            date_text = a.xpath("following::text()[contains(., '/')][1]").get("")
            date = date_text.strip() if date_text else ""

            yield response.follow(
                href,
                callback=self.parse_detail,
                cb_kwargs={"title": title, "date": date, "page": page},
            )

        # Phân trang: Lấy linh hoạt __EVENTTARGET từ link phân trang của trang web
        next_page_arg = str(page)
        event_target = None
        
        for href in response.css("a::attr(href)").getall():
            match = re.search(r"__doPostBack\('([^']+)','(\d+)'\)", href)
            if match and match.group(2) == next_page_arg:
                event_target = match.group(1)
                break

        if page < self.max_pages and event_target:
            yield FormRequest.from_response(
                response,
                formdata={"__EVENTTARGET": event_target, "__EVENTARGUMENT": next_page_arg},
                dont_click=True,
                dont_filter=True,
                callback=self.parse,
                cb_kwargs={"page": page + 1},
            )

    def parse_detail(self, response, title, date, page):
        # Lấy nội dung text thông thường (loại bỏ thẻ script, style, comment)
        texts = response.xpath(
            "//div[contains(@class,'n-desc')]//text()[not(ancestor::script) and not(ancestor::style) and normalize-space()]"
        ).getall()
        
        # Dọn dẹp khoảng trắng dư thừa
        clean_texts = [t.strip() for t in texts if t.strip()]
        content = " ".join(clean_texts)

        # Bóc tách dữ liệu bảng (table) nếu có
        tables_data = []
        for table in response.xpath("//table"):
            table_dict = []
            rows = table.xpath(".//tr")
            if not rows:
                continue
            
            # Lấy header từ dòng đầu tiên (có thể là th hoặc td)
            headers = [th.xpath("normalize-space()").get("") for th in rows[0].xpath(".//th|.//td")]
            
            for row in rows[1:]:
                cells = [td.xpath("normalize-space()").get("") for td in row.xpath(".//td")]
                if cells:
                    # Ráp header với cell nếu số lượng khớp
                    if len(headers) == len(cells) and any(headers):
                        table_dict.append(dict(zip(headers, cells)))
                    else:
                        table_dict.append(cells)
            if table_dict:
                tables_data.append(table_dict)

        attachments = [
            response.urljoin(h)
            for h in response.css("a::attr(href)").getall()
            if ATTACH_RE.search(h)
        ]

        yield {
            "title": title,
            "date": date,
            "type": classify(title),
            "page": page,
            "article_url": response.url,
            "content": content,
            "tables": tables_data,
            "attachments": sorted(set(attachments)),
        }