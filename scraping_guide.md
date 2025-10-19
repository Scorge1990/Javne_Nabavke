# 🌐 LegaBot Scraping Guide

This guide shows you how to scrape legal documents from external websites using your LegaBot scraper.

## ✅ **What You Can Scrape**

Your scraper works with any website that has legal documents in HTML format with the following structure:
- Articles with class `"clan"` (for titles)
- Text paragraphs with class `"normal"` (for content)

## 🚀 **Quick Start Examples**

### **1. Single External Website**
```bash
python scraper/scraper.py --url "https://www.paragraf.rs/propisi/zakon_o_radu.html" --output-dir scraper/laws
```

### **2. Multiple External Websites**
```bash
python scraper/scraper.py --file external_urls.txt --output-dir scraper/laws
```

### **3. Mixed Sources (External + Local)**
```bash
python scraper/scraper.py --file mixed_urls.txt --output-dir scraper/laws
```

## 📋 **Supported Websites**

### **Serbian Legal Websites:**
- **Paragraf.rs**: `https://www.paragraf.rs/propisi/`
- **Pravno-informacioni sistem**: `https://www.pravno-informacioni-sistem.rs/`
- **Sluzbeni glasnik**: `https://www.slglasnik.com/`

### **Example URLs:**
```
https://www.paragraf.rs/propisi/zakon_o_radu.html
https://www.paragraf.rs/propisi/zakon-o-porezu-na-dohodak-gradjana.html
https://www.paragraf.rs/propisi/zakon_o_zastiti_podataka_o_licnosti.html
https://www.paragraf.rs/propisi/zakon_o_zastiti_potrosaca.html
https://www.paragraf.rs/propisi/porodicni_zakon.html
```

## 🛠️ **How to Use**

### **Step 1: Create URL List**
Create a text file (e.g., `my_urls.txt`) with one URL per line:
```
https://www.paragraf.rs/propisi/zakon_o_radu.html
https://www.paragraf.rs/propisi/zakon_o_zastiti_potrosaca.html
http://localhost:8080/my_local_document.html
```

### **Step 2: Run the Scraper**
```bash
# From your project root directory
python scraper/scraper.py --file my_urls.txt --output-dir scraper/laws
```

### **Step 3: Check Results**
The scraper will create JSON files in the `scraper/laws/` directory:
```
scraper/laws/
├── zakon_o_radu.json
├── zakon_o_zastiti_potrosaca.json
└── my_local_document.json
```

## 📊 **Output Format**

Each scraped document becomes a JSON file with this structure:
```json
[
    {
        "title": "Član 1",
        "texts": [
            "Article content paragraph 1",
            "Article content paragraph 2"
        ],
        "link": "https://website.com/document.html#clan_1"
    },
    {
        "title": "Član 2",
        "texts": [
            "More article content..."
        ],
        "link": "https://website.com/document.html#clan_2"
    }
]
```

## 🔧 **Advanced Usage**

### **Custom Output Directory**
```bash
python scraper/scraper.py --file urls.txt --output-dir my_custom_folder
```

### **Single URL with Custom Output**
```bash
python scraper/scraper.py --url "https://example.com/law.html" --output-dir custom_laws
```

### **Verbose Output**
The scraper automatically shows progress and logs:
- ✅ Successful scrapes
- ❌ Failed requests
- 📊 Progress bars
- 📝 Detailed error messages

## 🌍 **International Websites**

Your scraper can work with legal websites from any country, as long as they use the expected HTML structure:

### **HTML Structure Required:**
```html
<p class="clan">
    <a name="article_1"></a>
    <strong>Article 1</strong> - Title
</p>
<p class="normal">Article content paragraph 1</p>
<p class="normal">Article content paragraph 2</p>
```

## ⚠️ **Important Notes**

### **Legal Considerations:**
- ✅ **Respect robots.txt** - Check if the website allows scraping
- ✅ **Rate limiting** - Don't overwhelm servers with too many requests
- ✅ **Terms of service** - Ensure you're allowed to scrape the content
- ✅ **Copyright** - Respect intellectual property rights

### **Technical Considerations:**
- 🌐 **Internet connection** required for external websites
- 🔒 **HTTPS/SSL** - Some sites may require secure connections
- 🚫 **Blocked requests** - Some sites may block automated requests
- ⏱️ **Timeouts** - Large documents may take time to process

## 🐛 **Troubleshooting**

### **Common Issues:**

1. **"Failed to fetch URL"**
   - Check internet connection
   - Verify URL is correct
   - Try accessing URL in browser first

2. **"Failed to scrape data"**
   - Website might not have expected HTML structure
   - Check if content is loaded dynamically (JavaScript)
   - Verify the page loads correctly

3. **"No articles found"**
   - Website might use different CSS classes
   - Content might be in different HTML structure
   - Check if the page has the expected format

### **Debug Steps:**
1. Open the URL in your browser
2. Check the HTML source code
3. Look for `<p class="clan">` and `<p class="normal">` elements
4. Verify the page structure matches expectations

## 📈 **Performance Tips**

- **Batch processing**: Use `--file` for multiple URLs
- **Parallel processing**: The scraper processes URLs sequentially for stability
- **Error handling**: Failed URLs don't stop the entire process
- **Progress tracking**: Built-in progress bars show completion status

## 🎯 **Best Practices**

1. **Start small**: Test with 1-2 URLs first
2. **Check results**: Verify the JSON output is correct
3. **Respect limits**: Don't scrape too aggressively
4. **Backup data**: Keep copies of important scraped content
5. **Monitor logs**: Watch for errors and warnings

## 📞 **Need Help?**

If you encounter issues:
1. Check the scraper logs for error messages
2. Verify the website structure matches expectations
3. Test with a known working URL first
4. Check your internet connection and firewall settings

---

**Happy Scraping! 🕷️📄**
