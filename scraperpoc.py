# from playwright import sync_api
#
# pw = sync_api.sync_playwright().start()
# browser = pw.chromium.launch(
#     channel="msedge",
#     headless=False,
#     slow_mo=5000
# )
# context = browser.new_context()
# page = context.new_page()
# page.goto("https://www.google.com")
# page2 = context.new_page()
# page2.goto("https://www.youtube.com")
#
# # browser2= pw.firefox.launch(
# #     channel="firefox",
# #     headless=False,
# #     slow_mo=5000
# # )
# # page = browser2.new_page()
# # page.goto("https://www.google.com")

import asyncio
from playwright.async_api import async_playwright

SEARCH_TERMS = ["python", "playwright", "openai", "machine learning", "data science"]


async def scrape_duckduckgo(context, term):
    page = await context.new_page()
    await page.goto("https://duckduckgo.com/")
    await page.wait_for_selector("input[name='q']")
    await page.fill("input[name='q']", term)
    await page.keyboard.press("Enter")
    await page.wait_for_selector("a.result__a")  # Esperamos a que carguen los resultados

    # Extraemos los primeros títulos y URLs
    links = await page.locator("a.result__a").all()
    print(f"\n🔎 Resultados para '{term}':")
    for link in links[:5]:
        title = await link.inner_text()
        href = await link.get_attribute("href")
        print(f"  • {title.strip()} ({href})")

    await context.close()

async def main():
    async with async_playwright() as playwright:
        # 🔹 Lanzamos UNA instancia de navegador
        browser = await playwright.chromium.launch(headless=False)

        # 🔹 Creamos un contexto por búsqueda
        tasks = []
        for term in SEARCH_TERMS:
            context = await browser.new_context()
            tasks.append(scrape_duckduckgo(context, term))

        await asyncio.gather(*tasks)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
