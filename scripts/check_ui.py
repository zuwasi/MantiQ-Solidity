"""Browser checks and optional tour recording against a running local demo server."""

import argparse
from pathlib import Path
import shutil

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8879")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute real toolchain through dashboard button",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record 32-second evidence tour, without audio",
    )
    args = parser.parse_args()
    assets = ROOT / "web" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url + "/")
        expect(page.locator(".count")).to_have_text("1 / 12")
        expect(page.locator(".prev")).to_be_hidden()
        page.screenshot(path=str(assets / "presentation.png"))
        page.keyboard.press("ArrowRight")
        expect(page.locator(".count")).to_have_text("2 / 12")
        page.keyboard.press("Space")
        expect(page.locator(".count")).to_have_text("3 / 12")
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(600)
        page.screenshot(path=str(assets / "defect-slide.png"))
        for _ in range(8):
            page.keyboard.press("ArrowRight")
        expect(page.locator(".count")).to_have_text("12 / 12")
        expect(page.locator(".next")).to_be_hidden()
        page.keyboard.press("ArrowRight")
        expect(page.locator(".count")).to_have_text("12 / 12")

        page.goto(args.url + "/dashboard.html")
        expect(page.locator("#defective")).to_contain_text("Released")
        expect(page.locator("#fixed")).to_contain_text("Funded")
        expect(page.locator("#pipeline .stage")).to_have_count(5)
        page.locator("#step").click()
        expect(page.locator(".stage.focus")).to_contain_text("Wolfram")
        page.locator("#reset").click()
        expect(page.locator(".stage.focus")).to_contain_text("Local EVM")
        page.locator("#play").click()
        page.wait_for_timeout(6200)
        expect(page.locator(".stage.focus")).to_contain_text("Wolfram")
        page.locator("#pause").click()
        page.wait_for_timeout(6200)
        expect(page.locator(".stage.focus")).to_contain_text("Wolfram")
        page.locator("#reset").click()
        with page.expect_download() as download:
            page.locator("#download").click()
        assert download.value.suggested_filename.startswith("mantiq-evidence-")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(assets / "dashboard.png"))

        if args.live:
            expect(page.locator("#run")).to_be_enabled()
            page.locator("#run").click()
            expect(page.locator("#run")).to_be_disabled()
            expect(page.locator("#mode")).to_have_text(
                "Live local run in progress", timeout=15000
            )
            expect(page.locator("#mode")).to_have_text(
                "Live local result", timeout=720000
            )
            expect(page.locator("#pipeline .failed")).to_have_count(0)
            expect(page.locator("#defective")).to_contain_text("Released")
            expect(page.locator("#fixed")).to_contain_text("Funded")
            page.screenshot(path=str(assets / "live-dashboard.png"))

        mobile = browser.new_page(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        mobile.goto(args.url + "/")
        mobile.screenshot(path=str(assets / "mobile-presentation.png"))
        # Dispatch touch events to exercise the actual swipe handler.
        mobile.evaluate("""() => {
          const el = document.querySelector('.slide');
          el.dispatchEvent(new TouchEvent('touchstart', {bubbles:true, touches:[new Touch({identifier:1,target:el,clientX:300,clientY:200})]}));
          el.dispatchEvent(new TouchEvent('touchend', {bubbles:true, changedTouches:[new Touch({identifier:1,target:el,clientX:200,clientY:200})]}));
        }""")
        expect(mobile.locator(".count")).to_have_text("2 / 12")
        mobile.goto(args.url + "/dashboard.html")
        expect(mobile.locator("#fixed")).to_contain_text("Funded")
        assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
        mobile.screenshot(path=str(assets / "mobile-dashboard.png"), full_page=True)
        mobile.close()

        # Explicitly mock only the failure-state UI check, never published evidence.
        failure = browser.new_page()
        failure.route(
            "**/evidence/replay.json",
            lambda route: route.fulfill(status=404, body="missing"),
        )
        failure.route(
            "**/api/status", lambda route: route.fulfill(status=404, body="missing")
        )
        failure.goto(args.url + "/dashboard.html")
        expect(failure.locator("#mode")).to_have_text("Missing evidence")
        expect(failure.locator("#download")).to_be_disabled()
        expect(failure.locator("#run")).to_be_disabled()
        expect(failure.locator("#pipeline .passed")).to_have_count(0)
        failure.close()

        if args.record:
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000},
                record_video_dir=str(ROOT / "runs" / "video"),
                record_video_size={"width": 1440, "height": 1000},
            )
            video_page = context.new_page()
            # Record the public replay experience, never present cached API results as live.
            video_page.route(
                "**/api/status",
                lambda route: route.fulfill(status=404, body="static replay"),
            )
            video_page.goto(args.url + "/dashboard.html?autoplay=1")
            expect(video_page.locator("#mode")).to_have_text("Recorded evidence replay")
            video_page.wait_for_timeout(32000)
            video = video_page.video
            context.close()
            shutil.copyfile(video.path(), assets / "demo-tour.webm")
        assert not errors, errors
        browser.close()
    print(
        "PASS desktop/mobile slides, navigation, tour, download, missing evidence, overflow"
        + (", live execution" if args.live else "")
        + (", recording" if args.record else "")
    )


if __name__ == "__main__":
    main()
