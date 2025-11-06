from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def decode_google_news_url(encoded_url):
    """
    Decode a Google News RSS redirect URL using Selenium to follow the redirect.
    
    Args:
        encoded_url: The full Google News redirect URL
        
    Returns:
        The final destination URL or None if request fails
    """
    driver = None
    try:
        print(f"Following redirect for: {encoded_url}\n")
        
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Initialize the Chrome driver
        driver = webdriver.Chrome(options=chrome_options)
        
        # Set page load timeout
        driver.set_page_load_timeout(30)
        
        # Navigate to the URL
        driver.get(encoded_url)
        
        # Wait a bit for any redirects to complete
        time.sleep(3)
        
        # Get the final URL after redirect
        final_url = driver.current_url
        
        # Check if we actually got redirected away from Google News
        if 'news.google.com' not in final_url:
            print(f"Final URL: {final_url}")
            
            # Extract domain
            from urllib.parse import urlparse
            parsed = urlparse(final_url)
            print(f"Domain: {parsed.netloc}")
            
            return final_url
        else:
            # Sometimes we need to wait longer or click through
            print("Still on Google News, waiting longer...")
            time.sleep(5)
            final_url = driver.current_url
            
            if 'news.google.com' not in final_url:
                print(f"Final URL: {final_url}")
                from urllib.parse import urlparse
                parsed = urlparse(final_url)
                print(f"Domain: {parsed.netloc}")
                return final_url
            else:
                print("Redirect didn't complete. URL still pointing to Google News.")
                return None
        
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        # Always close the browser
        if driver:
            driver.quit()


# Example usage
if __name__ == "__main__":
    # Your URL
    url = "https://news.google.com/rss/articles/CBMilgFBVV95cUxPNXNwRTB0YjFMUE0teXY2azZQQ0k5NGEtV0E2UzVXUGRzYmFUemQzQmdXWmZIY2FXbDBaUlhBY2poNlBxZGpQbERhRm5KWWM4bGdkS183UHhWZmlySFZRRmpmUzJFUFlJb0N3N2d1Ti1VbmZyR0E0MGFpTS1POEJ4Y0ZrN1hOaTF0SC12OE1IYXRWVnZfVVE?oc=5"
    
    final_url = decode_google_news_url(url)
    
    if final_url:
        print(f"\n✓ Successfully resolved the URL")
    else:
        print(f"\n✗ Failed to resolve the URL")