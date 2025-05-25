from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
import re


class ChromeTabManager:
    def __init__(self):
        self.driver = None
        self.tabs = {}  # Maps user query to window handle
        self.base_handle = None
        self.is_base_used = False

    def _initialize_driver(self):
        """Initialize the Chrome driver only when needed"""
        if self.driver is None:
            print("Initializing Chrome browser...")
            options = Options()
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            # Remove the remote debugging port that might cause conflicts
            # options.add_argument("--remote-debugging-port=9222")

            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=options
            )
            # Give it a moment to fully initialize
            # time.sleep(1)
            self.base_handle = self.driver.current_window_handle

    def search(self, query):
        self._initialize_driver()  # Initialize when first search is called

        if not self.is_base_used:
            print(f"[🔍] Searching for: {query}")
            self.driver.get(f"https://www.google.com/search?q={query}")
            self.tabs[query] = self.base_handle
            self.is_base_used = True
        else:
            print(f"[🔍] Searching for: {query} (new tab)")
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(f"https://www.google.com/search?q={query}")
            self.tabs[query] = self.driver.current_window_handle

        # Minimize after the search is done
        self.driver.maximize_window()
        self.driver.switch_to.window(self.driver.window_handles[-1])

    def list_tabs(self):
        if self.driver is None:
            print("No browser session active. Search something first!")
            return
        
        browsers = []
        browser_info = {"name": "google chrome", "windows": []}
        print("Currently opened tabs:")
        for handle in self.driver.window_handles:
            try:
                self.driver.switch_to.window(handle)
                title = self.driver.title or "Untitled"
                browser_info["windows"].append(title.strip())
                # browsers.append(browser_info)
                print(f"  - {title.strip()}")
            except:
                continue  # In case a tab was closed manually mid-loop
        time.sleep(0.5)
        self.driver.minimize_window()
        return browsers
    
    def close_tab(self, keyword):
        if self.driver is None:
            print("No browser session active. Search something first!")
            return

        
        keyword = keyword.lower()
        for handle in self.driver.window_handles:
            try:
                self.driver.switch_to.window(handle)
                time.sleep(0.5)
                title = self.driver.title.lower()
                if keyword in title:
                    self.driver.close()
                    print(f"Closed tab with title: {title}")
                    self.driver.minimize_window()
                    return
            except:
                continue
        print(f"No tab with '{keyword}' found to close.")

    def quit_browser(self):
        """Safely quit the browser if it exists"""
        if self.driver:
            try:
                self.driver.quit()
                print("[✅] Browser closed successfully.")
            except:
                pass
        else:
            print("[ℹ️] No browser session to close.")

def main():
    manager = ChromeTabManager()
    print("\n[Chrome Tab Manager Ready]")
    print("Commands:\n - search query\n - close\n - close keyword\n - exit\n")

    while True:
        try:
            cmd = input(">>> ").strip()

            if cmd.lower().startswith("search "):
                query = cmd[7:].strip()  # Extract query string after 'search '
                if query:
                    manager.search(query)  # Pass single string, not list
                else:
                    print("[⚠️] Please provide a search query.")

            elif cmd.lower().startswith("close"):
                keyword = cmd[len("close") :].strip()
                if keyword:
                    manager.close_tab(keyword)
                else:
                    manager.list_tabs()

            elif cmd.lower() == "exit":
                print("Exiting...")
                break

            else:
                print("[?] Unknown command. Try again.")
        except KeyboardInterrupt:
            break

    manager.quit_browser()


if __name__ == "__main__":
    main()
