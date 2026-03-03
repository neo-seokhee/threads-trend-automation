import os
import json
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright
import google.generativeai as genai
import requests

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경변수 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

genai.configure(api_key=GEMINI_API_KEY)

def scrape_threads():
      """Threads에서 트렌드 데이터 스크래핑"""
      logger.info("🕷️ Threads 스크래핑 시작...")

    try:
              with sync_playwright() as p:
                            browser = p.chromium.launch(headless=True)
                            page = browser.new_page()
                            page.goto("https://www.threads.com", timeout=30000)
                            page.wait_for_load_state("networkidle", timeout=10000)

            # 페이지 콘텐츠 추출
                  content = page.content()

            # 텍스트 추출 (간단한 파싱)
            text_content = page.evaluate("""
                            () => {
                                                const posts = Array.from(document.querySelectorAll('[role="article"]'));
                                                                    return posts.slice(0, 10).map(post => {
                                                                                            const text = post.innerText;
                                                                                                                    const likes = post.querySelector('[aria-label*="좋아요"]')?.innerText || "0";
                                                                                                                                            return { text: text.substring(0, 300), likes: likes };
                                                                                                                                                                });
                                                                                                                                                                                }
                                                                                                                                                                                            """)

            browser.close()
            logger.info(f"✅ {len(text_content)}개 게시물 수집 완료")
            return text_content

except Exception as e:
        logger.error(f"❌ 스크래핑 실패: {str(e)}")
        return []

def analyze_with_gemini(content):
      """Gemini로 트렌드 분석"""
    logger.info("🤖 Gemini로 분석 중...")

    try:
              # 콘텐츠를 텍스트로 변환
              text_data = json.dumps(content, ensure_ascii=False)

        prompt = f"""다음은 Threads의 최근 인기 게시물들입니다.

        {text_data}

        이 게시물들을 분석해서 다음 형식으로 오늘의 주요 트렌드 5가지를 요약해줘:

        📊 *오늘의 Threads 트렌드 요약* ({datetime.now().strftime('%Y.%m.%d')})

        1️⃣ *트렌드명1*
        - 설명 (1-2줄)

        2️⃣ *트렌드명2*
        - 설명 (1-2줄)

        (이런 식으로 5개까지)

        마지막에는:
        _📌 출처: Threads 추천 피드 기준 | 분석: Gemini API_

        라고 추가해줘."""

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        logger.info("✅ 분석 완료")
        return response.text

except Exception as e:
        logger.error(f"❌ 분석 실패: {str(e)}")
        return None

def send_slack_message(summary):
      """Slack에 메시지 전송"""
    logger.info("📤 Slack 메시지 전송 중...")

    try:
              payload = {
                  "text": summary
    }

        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)

        if response.status_code == 200:
                      logger.info("✅ Slack 전송 완료!")
else:
            logger.error(f"❌ Slack 전송 실패 (상태코드: {response.status_code})")

except Exception as e:
        logger.error(f"❌ Slack 전송 중 에러: {str(e)}")

def main():
      """메인 함수"""
    logger.info("=" * 50)
    logger.info("Threads 트렌드 자동화 시작")
    logger.info("=" * 50)

    # 1. Threads 스크래핑
    threads_data = scrape_threads()

    if not threads_data:
              logger.error("게시물 수집 실패. 프로세스 종료.")
              return

    # 2. Gemini로 분석
    summary = analyze_with_gemini(threads_data)

    if not summary:
              logger.error("분석 실패. 프로세스 종료.")
              return

    # 3. Slack으로 전송
    send_slack_message(summary)

    logger.info("=" * 50)
    logger.info("✅ 모든 작업 완료!")
    logger.info("=" * 50)

if __name__ == "__main__":
      main()
