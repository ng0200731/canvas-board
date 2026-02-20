import os
import config


def export_board(share_id, fmt="png"):
    """Export a shared board as PDF or PNG using Playwright."""
    from playwright.sync_api import sync_playwright

    output_dir = os.path.join(config.BASE_DIR, ".tmp")
    os.makedirs(output_dir, exist_ok=True)

    ext = "pdf" if fmt == "pdf" else "png"
    output_path = os.path.join(output_dir, f"export_{share_id}.{ext}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(f"http://127.0.0.1:5000/s/{share_id}")
        page.wait_for_timeout(2000)  # Wait for cards and lines to render

        if fmt == "pdf":
            page.pdf(path=output_path, format="A3", landscape=True)
        else:
            page.screenshot(path=output_path, full_page=True)

        browser.close()

    return output_path
