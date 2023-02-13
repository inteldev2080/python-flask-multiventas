class MoneyChange:
    @staticmethod
    def get_dollar():
        return 23.01
        import ssl
        import urllib.request
        from bs4 import BeautifulSoup
        ssl._create_default_https_context = ssl._create_unverified_context

        url = "https://www.bcv.org.ve"

        page = urllib.request.urlopen(url=url)
        soup = BeautifulSoup(page, "html.parser")
        element = soup.find(id="dolar").strong.text
        element = element.strip()
        element = element.replace(",", ".")
        return round( float(element), 2)