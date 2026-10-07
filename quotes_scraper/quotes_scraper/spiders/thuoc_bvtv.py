import re
import scrapy
from scrapy import FormRequest

ATTACH_RE = re.compile(r"\.(pdf|docx?|xlsx?|zip|rar)(\?.*)?$", re.I)

def classify(title: str) -> str:
    """Phân loại thông báo theo tiêu đề để dễ so sánh/thống kê sau này."""
    t = title.lower()
    if "danh sách" in t:
        return "danh_sach"
    if "quyết định" in t:
        return "quyet_dinh"
    if "thông tư" in t:
        return "thong_tu"
    if "cấp giấy chứng nhận" in t:
        return "cap_giay_chung_nhan"
    return "khac"

class PpdThuocBvtvSpider(scrapy.Spider):
    name = "ppd_thuoc_bvtv"
    allowed_domains = ["ppd.gov.vn", "drive.google.com"]
    start_urls = ["https://www.ppd.gov.vn/thuoc-bao-ve-thuc-vat-67.html"]

    max_pages = 10  # giới hạn số trang cần cào

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 1.5,
        "AUTOTHROTTLE_ENABLED": True,
        "FEEDS": {"thuoc_bvtv.json": {"format": "json", "encoding": "utf8", "overwrite": True}},
    }

    def parse(self, response, page=1):
        # Lấy các thẻ a trỏ tới bài viết chi tiết
        for a in response.xpath("//a[contains(@href, '.html')]"):
            href = a.xpath("@href").get()
            title = a.xpath("normalize-space()").get("").strip()
            
            # Bỏ qua các link ngắn (menu) hoặc không chứa text
            if not href or len(title) < 20:
                continue
            
            # Dấu hiệu nhận biết link bài viết (loại bỏ các link trang chủ, chuyên mục chung)
            if 'tin-moi-nhat' not in href and 'thuoc-bao-ve-thuc-vat-67/' not in href and 'van-ban-chinh-sach/' not in href:
                continue
            
            # LỌC THÔNG MINH BẰNG TIÊU ĐỀ: Bỏ qua các tin tức sự kiện, hội nghị
            title_lower = title.lower()
            ignore_keywords = ["giấy mời", "khai giảng", "hội thảo", "hội nghị", "lễ công bố", "tập huấn", "hội nghị trực tuyến", "đình chỉ hiệu lực"]
            if any(k in title_lower for k in ignore_keywords):
                self.logger.info(f"BỎ QUA TIN TỨC: {title}")
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

        # Bóc tách dữ liệu bảng (table) nếu có (phòng trường hợp 1 số trang hiếm hoi có bảng)
        tables_data = []
        for table in response.xpath("//table"):
            table_dict = []
            rows = table.xpath(".//tr")
            if not rows:
                continue
            
            # Lấy header từ dòng đầu tiên
            headers = [th.xpath("normalize-space()").get("") for th in rows[0].xpath(".//th|.//td")]
            
            for row in rows[1:]:
                cells = [td.xpath("normalize-space()").get("") for td in row.xpath(".//td")]
                if cells:
                    if len(headers) == len(cells) and any(headers):
                        table_dict.append(dict(zip(headers, cells)))
                    else:
                        table_dict.append(cells)
            if table_dict:
                tables_data.append(table_dict)

        # TÌM TẤT CẢ FILE ĐÍNH KÈM + LINK GOOGLE DRIVE
        attachments = []
        for h in response.css("a::attr(href)").getall():
            if ATTACH_RE.search(h) or "drive.google.com" in h:
                attachments.append(response.urljoin(h))

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
