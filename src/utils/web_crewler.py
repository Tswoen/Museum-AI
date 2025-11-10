import requests
from bs4 import BeautifulSoup
import time
import json
import re

class HubeiMuseumScraper:
    def __init__(self):
        self.base_url = "http://hbsbwg.cjyun.org"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_list_page(self, url):
        """获取列表页"""
        try:
            response = self.session.get(url)
            response.encoding = 'utf-8'
            if response.status_code == 200:
                return response.text
            else:
                print(f"请求失败，状态码：{response.status_code}")
                return None
        except Exception as e:
            print(f"请求出错：{e}")
            return None
    
    def parse_list_page(self, html):
        """解析列表页，获取文物基本信息"""
        soup = BeautifulSoup(html, 'html.parser')
        artifacts = []
        
        # 找到文物列表容器
        mainlist = soup.find('div', {'id': 'mainlist', 'class': 'mainlist'})
        if not mainlist:
            print("未找到文物列表")
            return artifacts
        
        # 找到所有文物项
        artifact_items = mainlist.find_all('li')
        print(f"找到 {len(artifact_items)} 个文物项")
        
        for item in artifact_items:
            try:
                # 方法1：从h4标签获取名称
                name_tag = item.find('h4', class_='normal')
                if name_tag:
                    name = name_tag.get_text(strip=True)
                    print(f"从h4找到文物名称: {name}")
                else:
                    # 方法2：从h5标签获取名称（详情页的相关文物使用h5）
                    name_tag = item.find('h5', class_='normal')
                    if name_tag:
                        name = name_tag.get_text(strip=True)
                        print(f"从h5找到文物名称: {name}")
                    else:
                        # 方法3：从链接文本获取
                        name_links = item.find_all('a')
                        for link in name_links:
                            link_text = link.get_text(strip=True)
                            if link_text and len(link_text) > 1 and not link_text.startswith('http'):
                                name = link_text
                                print(f"从链接文本找到文物名称: {name}")
                                break
                        else:
                            name = "未知名称"
                
                # 获取图片URL
                img_tag = item.find('img', {'class': 'upmove'})
                if img_tag and img_tag.get('src'):
                    img_url = img_tag['src']
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = self.base_url + img_url
                else:
                    img_url = ""
                
                # 获取详情页链接
                detail_url = ""
                # 优先从图片链接获取
                detail_link_tag = item.find('a', {'class': 'list_photo'})
                if detail_link_tag and detail_link_tag.get('href'):
                    detail_url = detail_link_tag['href']
                else:
                    # 从名称链接获取
                    name_link = item.find('a', href=re.compile(r'/yuqi/p/'))
                    if name_link and name_link.get('href'):
                        detail_url = name_link['href']
                
                # 补全URL
                if detail_url:
                    if detail_url.startswith('/'):
                        detail_url = self.base_url + detail_url
                    elif not detail_url.startswith(('http://', 'https://')):
                        detail_url = self.base_url + '/' + detail_url
                
                artifact = {
                    'name': name,
                    'image_url': img_url,
                    'detail_url': detail_url,
                    'description': ""  # 将在详情页中获取
                }
                
                artifacts.append(artifact)
                
            except Exception as e:
                print(f"解析文物项时出错：{e}")
                continue
        
        return artifacts
    
    def get_detail_page(self, detail_url):
        """获取详情页"""
        try:
            response = self.session.get(detail_url)
            response.encoding = 'utf-8'
            if response.status_code == 200:
                return response.text
            else:
                print(f"请求详情页失败，状态码：{response.status_code}")
                return None
        except Exception as e:
            print(f"请求详情页出错：{e}")
            return None
    
    def parse_detail_page(self, html):
        """解析详情页，获取文物描述"""
        soup = BeautifulSoup(html, 'html.parser')
        description = ""
        
        print("正在解析详情页结构...")  # 调试信息
        
        # 方法1：查找文章内容区域 - 根据提供的HTML结构
        article_content = soup.find('div', class_='article_content')
        if article_content:
            print("找到article_content区域")
            # 获取所有段落文本
            paragraphs = article_content.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 10:  # 排除空文本和过短的文本
                    if description:
                        description += " " + text
                    else:
                        description = text
            print(f"从article_content获取描述: {description[:100]}...")
        
        # 方法2：如果方法1没有找到描述，尝试从meta标签获取
        if not description:
            meta_description = soup.find('meta', attrs={'name': 'description'})
            if meta_description and meta_description.get('content'):
                description = meta_description['content'].strip()
                print(f"从meta description获取描述: {description[:100]}...")
        
        # 方法3：查找其他可能的内容区域
        if not description:
            # 查找包含文物信息的其他div
            content_divs = soup.find_all('div', class_=re.compile(r'content|info|detail|text'))
            for div in content_divs:
                # 排除已经检查过的article_content
                if 'article_content' not in div.get('class', []):
                    text = div.get_text(strip=True)
                    if len(text) > 50 and not any(keyword in text for keyword in ['导航', '首页', '分享', '版权']):
                        description = text
                        print(f"从其他内容区域获取描述: {description[:100]}...")
                        break
        
        # 方法4：从整个页面提取主要文本内容
        if not description:
            print("尝试从整个页面提取文本...")
            all_text = soup.get_text()
            # 分割文本并找到最长的有意义的段落
            text_blocks = re.split(r'\n\s*\n', all_text)
            meaningful_blocks = []
            for block in text_blocks:
                clean_block = re.sub(r'\s+', ' ', block).strip()
                # 排除导航、版权等无关内容，选择包含文物信息的文本
                if (len(clean_block) > 30 and 
                    not any(keyword in clean_block for keyword in 
                        ['首页', 'Copyright', '版权所有', '导航', '返回顶部', '分享', '微信', '微博'])):
                    meaningful_blocks.append(clean_block)
            
            if meaningful_blocks:
                # 选择最长的有意义的文本块
                description = max(meaningful_blocks, key=len)
                print(f"从整个页面提取描述: {description[:100]}...")
        
        # 方法5：查找文物基本信息（年代、出土信息等）
        if not description:
            # 查找可能包含文物基本信息的元素
            h2_title = soup.find('h2')
            if h2_title:
                title_text = h2_title.get_text(strip=True)
                # 如果标题包含文物名称，尝试获取相邻的描述信息
                next_elements = h2_title.find_next_siblings()
                for elem in next_elements:
                    if elem.name == 'p':
                        text = elem.get_text(strip=True)
                        if text and len(text) > 10:
                            description = text
                            print(f"从标题相邻元素获取描述: {description[:100]}...")
                            break
        
        # 清理描述文本
        if description:
            description = re.sub(r'\s+', ' ', description).strip()
            # 移除可能的多余空白字符
            description = re.sub(r'[\r\n\t]', ' ', description)
        
        # 如果仍然没有找到描述，尝试从keywords中获取信息
        if not description:
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords and meta_keywords.get('content'):
                keywords = meta_keywords['content']
                if keywords:
                    description = f"关键词: {keywords}"
                    print(f"从keywords生成描述: {description}")
        
        print(f"最终获取的描述长度: {len(description)} 字符")
        return description
    
    def scrape_all_artifacts(self, start_url=None):
        """爬取所有文物信息"""
        if not start_url:
            # start_url = "http://hbsbwg.cjyun.org/yuqi/index.html"
            start_url = "http://hbsbwg.cjyun.org/qtq/index.html"
            
        
        print("开始爬取文物列表...")
        html = self.get_list_page(start_url)
        if not html:
            return []
        
        artifacts = self.parse_list_page(html)
        print(f"从列表页获取到 {len(artifacts)} 个文物基本信息")
        
        # 获取每个文物的详细描述
        for i, artifact in enumerate(artifacts):
            print(f"正在处理第 {i+1}/{len(artifacts)} 个文物: {artifact['name']}")
            
            if artifact['detail_url']:
                detail_html = self.get_detail_page(artifact['detail_url'])
                if detail_html:
                    description = self.parse_detail_page(detail_html)
                    artifact['description'] = description
                else:
                    artifact['description'] = "无法获取描述"
            else:
                artifact['description'] = "无详情页链接"
            
            # 添加延迟，避免请求过于频繁
            time.sleep(1)
        
        return artifacts
    
    def save_to_json(self, artifacts, filename="hubei_museum_qtq.json"):
        """保存结果到JSON文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(artifacts, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到 {filename}")
    
    def save_to_csv(self, artifacts, filename="hubei_museum_qtq.csv"):
        """保存结果到CSV文件"""
        import csv
        
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['名称', '图片URL', '详情页URL', '描述'])
            
            for artifact in artifacts:
                writer.writerow([
                    artifact['name'],
                    artifact['image_url'],
                    artifact['detail_url'],
                    artifact['description'].replace('\n', ' ').replace('\r', ' ')
                ])
        print(f"数据已保存到 {filename}")

def main():
    scraper = HubeiMuseumScraper()
    
    # 爬取文物信息
    artifacts = scraper.scrape_all_artifacts()
    
    if artifacts:
        print(f"\n成功爬取 {len(artifacts)} 个文物信息：")
        for i, artifact in enumerate(artifacts, 1):
            print(f"\n{i}. {artifact['name']}")
            print(f"   图片: {artifact['image_url']}")
            print(f"   详情: {artifact['detail_url']}")
            print(f"   描述: {artifact['description'][:100]}..." if len(artifact['description']) > 100 else f"   描述: {artifact['description']}")
        
        # 保存结果
        scraper.save_to_json(artifacts)
        scraper.save_to_csv(artifacts)
    else:
        print("未获取到任何文物信息")

if __name__ == "__main__":
    main()