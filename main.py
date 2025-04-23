import time
import os
import urllib.parse
import psutil
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

class QueryTabManager:
    def __init__(self):
        # Prompt user for profile choice
        profile_choice = input("Do you want to use your default Chrome profile (requires closing all Chrome instances) or a separate profile? (default/separate): ").strip().lower()
        
        chrome_options = webdriver.ChromeOptions()
        self.profile_dir = None
        if profile_choice == "default":
            # Use default Chrome profile
            if self.is_chrome_running():
                print("Please close all Chrome instances to use the default profile.")
                self.wait_for_chrome_to_close()
            self.profile_dir = os.path.join(os.getenv("LOCALAPPDATA"), "Google", "Chrome", "User Data")
            chrome_options.add_argument(f"--user-data-dir={self.profile_dir}")
            chrome_options.add_argument("--profile-directory=Default")
            print("Using default Chrome profile. Google should be logged in if previously set up.")
        else:
            # Use or create a separate profile
            self.profile_dir = os.path.join(os.getenv("LOCALAPPDATA"), "ChromeScriptProfile")
            os.makedirs(self.profile_dir, exist_ok=True)
            chrome_options.add_argument(f"--user-data-dir={self.profile_dir}")
            chrome_options.add_argument("--profile-directory=Default")
            print("Using separate Chrome profile. Checking Google login status...")

        # Automatically install ChromeDriver
        service = Service(ChromeDriverManager().install())
        
        # Initialize WebDriver
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.query_tabs = []  # List of (query, window_handle) tuples
        
        # Check Google login for separate profile
        if profile_choice != "default":
            self.check_google_login()
        
        self.driver.get("chrome://newtab")  # Start with a blank page
        print("To include existing tabs, use the 'import' command with a query or URL.")

    def is_chrome_running(self):
        """Check if any Chrome instances are running"""
        for process in psutil.process_iter(['name']):
            if process.info['name'].lower() == 'chrome.exe':
                return True
        return False

    def wait_for_chrome_to_close(self):
        """Wait until all Chrome instances are closed"""
        while self.is_chrome_running():
            print("Waiting for Chrome instances to close... (Press Ctrl+C to cancel)")
            time.sleep(2)
        print("All Chrome instances closed.")

    def check_google_login(self):
        """Check if Google is logged in; if not, prompt for manual login in regular Chrome"""
        try:
            self.driver.get("https://accounts.google.com")
            time.sleep(2)  # Wait for page to load
            title = self.driver.title.lower()
            if "sign in" in title or "log in" in title:
                print("Google is not logged in. Selenium cannot sign in due to security restrictions.")
                print(f"To log in, we will open Chrome with the separate profile ({self.profile_dir}).")
                self.driver.quit()  # Close Selenium instance
                self.manual_google_login()
                # Reinitialize WebDriver after manual login
                chrome_options = webdriver.ChromeOptions()
                chrome_options.add_argument(f"--user-data-dir={self.profile_dir}")
                chrome_options.add_argument("--profile-directory=Default")
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                print("Resumed with logged-in profile.")
            else:
                print("Google appears to be logged in.")
        except WebDriverException as e:
            print(f"Error checking Google login: {e}. Attempting manual login.")
            self.driver.quit()
            self.manual_google_login()
            # Reinitialize WebDriver
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument(f"--user-data-dir={self.profile_dir}")
            chrome_options.add_argument("--profile-directory=Default")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("Resumed with logged-in profile.")

    def manual_google_login(self):
        """Launch regular Chrome for manual Google login"""
        chrome_path = self.find_chrome_executable()
        if not chrome_path:
            raise Exception("Could not find Chrome executable. Please ensure Chrome is installed.")
        
        print(f"Launching Chrome with profile: {self.profile_dir}")
        print("Please log in to Google, then close the Chrome window to continue.")
        subprocess.run([
            chrome_path,
            f"--user-data-dir={self.profile_dir}",
            "--profile-directory=Default",
            "https://accounts.google.com"
        ])
        print("Chrome closed. Assuming Google login completed.")

    def find_chrome_executable(self):
        """Find Chrome executable path"""
        possible_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.getenv("PROGRAMFILES"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.getenv("PROGRAMFILES(x86)"), "Google", "Chrome", "Application", "chrome.exe")
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def open_query(self, query):
        # Reuse the initial tab if no queries exist, otherwise open a new tab
        if not self.query_tabs and len(self.driver.window_handles) == 1:
            handle = self.driver.window_handles[0]
            self.driver.switch_to.window(handle)
        else:
            self.driver.execute_script("window.open('');")
            handle = self.driver.window_handles[-1]
            self.driver.switch_to.window(handle)
                  
        # Perform Google search for the query
        self.driver.get(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        self.query_tabs.append((query, handle))
        print(f"Opened tab for query: {query}")

    def import_tab(self, input_str):
        # Handle user-provided query or URL
        input_str = input_str.strip()
        if input_str.startswith("http"):
            # Assume it’s a URL
            query = self.extract_query_from_url(input_str)
            if not query:
                query = input_str  # Fallback to URL as query
        else:
            # Treat as a query
            query = input_str
        
        # Open the tab
        self.driver.execute_script("window.open('');")
        new_handle = self.driver.window_handles[-1]
        self.driver.switch_to.window(new_handle)
        self.driver.get(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        self.query_tabs.append((query, new_handle))
        print(f"Imported tab for query: {query}")

    def extract_query_from_url(self, url):
        # Extract query from Google search URL
        if "google.com/search" in url:
            parsed_url = urllib.parse.urlparse(url)
            query_dict = urllib.parse.parse_qs(parsed_url.query)
            return query_dict.get("q", [""])[0].replace("+", " ")
        return None

    def detect_manual_tabs(self):
        """Detect new tabs opened manually in the Selenium instance"""
        current_handles = self.driver.window_handles
        known_handles = [handle for _, handle in self.query_tabs]
        
        for handle in current_handles:
            if handle not in known_handles:
                try:
                    self.driver.switch_to.window(handle)
                    url = self.driver.current_url
                    # Check if it's a Google search URL
                    if "google.com/search" in url:
                        query = self.extract_query_from_url(url)
                        if query and (query, handle) not in self.query_tabs:
                            self.query_tabs.append((query, handle))
                            print(f"Detected manually opened query: {query}")
                except WebDriverException:
                    continue

    def update_query_list(self):
        """Remove queries for tabs that were manually closed"""
        valid_tabs = []
        for query, handle in self.query_tabs:
            try:
                self.driver.switch_to.window(handle)
                valid_tabs.append((query, handle))  # Tab is still open
            except WebDriverException:
                print(f"Detected closed tab for query: {query}")
                continue
        self.query_tabs = valid_tabs

    def list_queries(self):
        self.detect_manual_tabs()  # Check for new manual tabs
        self.update_query_list()  # Remove closed tabs
        if not self.query_tabs:
            print("No queries opened.")
            return
        print("\nOpened Queries:")
        for i, (query, _) in enumerate(self.query_tabs, 1):
            print(f"{i}. {query}")

    def close_tab(self, query):
        self.detect_manual_tabs()  # Update before closing
        self.update_query_list()  # Ensure list is current
        for q, handle in self.query_tabs:
            if query.lower() == q.lower():
                try:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
                    self.query_tabs.remove((q, handle))
                    print(f"Closed tab for query: {query}")
                    if self.driver.window_handles:  # Switch to first available tab
                        self.driver.switch_to.window(self.driver.window_handles[0])
                    return True
                except WebDriverException as e:
                    print(f"Error closing tab: {e}")
                    return False
        print(f"No tab found for query: {query}")
        return False

    def run(self):
        print("Query Tab Manager: Type a query to open a tab, 'close' to list queries, 'close <query>' to close a tab, 'import <query or URL>' to add existing tabs, or 'exit' to quit.")
        while True:
            command = input("> ").strip()
            if command.lower() == "exit":
                self.driver.quit()
                print("Exiting.")
                break
            elif command.lower() == "close":
                self.list_queries()
            elif command.lower().startswith("close "):
                query = command[6:].strip()
                self.close_tab(query)
            elif command.lower().startswith("import "):
                input_str = command[7:].strip()
                self.import_tab(input_str)
            else:
                self.open_query(command)

if __name__ == "__main__":
    try:
        manager = QueryTabManager()
        manager.run()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            manager.driver.quit()
        except:
            pass
