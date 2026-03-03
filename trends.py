import os
import json
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright
import google.generativeai as genai
import requests
import time

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경변수 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

genai.configure(api_key=GEMINI_API_KEY)

def scrape_threads_posts(num_posts=100):
          """Threads에서 최대 100개의 게시물 스크래핑"""
          logger.info(f"🕷️ Threads에서 {num_posts}개 게시물 스크래핑 시작...")

    try:
                  with sync_playwright() as p:
                                    browser = p.chromium.launch(headless=True)
                                    page = browser.new_page()
                                    page.goto("https://www.threads.com", timeout=30000)
                                    page.wait_for_load_state("networkidle", timeout=10000)

            posts_data = []
            last_height = 0
            scroll_count = 0
            max_scrolls = 20  # 최대 20번 스크롤 (100개 수집하기 위해)

            while len(posts_data) < num_posts and scroll_count < max_scrolls:
                                  # 현재 페이지의 게시물 추출
                                  current_posts = page.evaluate("""
                                                      () => {
                                                                              const posts = Array.from(document.querySelectorAll('[role="article"]'));
                                                                                                      return posts.map(post => {
                                                                                                                                  try {
                                                                                                                                                                  const text = post.innerText;
                                                                                                                                                                                                  const author = post.querySelector('[href*="@"]')?.textContent || "Unknown";
                                                                                                                                                                                                                                  const timestamp = post.querySelector('[dir="ltr"]')?.textContent || "";
                                                                                                                                                                                                                                                                  
                                                                                                                                                                                                                                                                                                  // 좋아요 수 추출
                                                                                                                                                                                                                                                                                                                                  const likeElements = post.querySelectorAll('button');
                                                                                                                                                                                                                                                                                                                                                                  let likes = "0";
                                                                                                                                                                                                                                                                                                                                                                                                  for (let elem of likeElements) {
                                                                                                                                                                                                                                                                                                                                                                                                                                      const ariaLabel = elem.getAttribute('aria-label');
                                                                                                                                                                                                                                                                                                                                                                                                                                                                          if (ariaLabel && ariaLabel.includes('좋아요')) {
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  likes = ariaLabel.replace(/[^0-9]/g, '') || "0";
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          break;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              }
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              }
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              return {
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  text: text.substring(0, 500),
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      author: author,
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          likes: likes,
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              timestamp: timestamp
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              };
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          } catch (e) {
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          return null;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      }
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              }).filter(p => p !== null && p.text.length > 10);
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  }
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  """)

                # 중복 제거하고 추가
                                  for post in current_posts:
                                                            if len(posts_data) < num_posts:
                                                                                          if not any(p['text'][:100] == post['text'][:100] for p in posts_data):
                                                                                                                            posts_data.append(post)
                                                                                                                
                                                                                  logger.info(f"현재 수집된 게시물: {len(posts_data)}/{num_posts}")

                # 스크롤
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                                          # 더 이상 로드할 내용이 없음
                                          break

                page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                last_height = new_height
                scroll_count += 1

                # 로딩 대기
                time.sleep(2)

            browser.close()
            logger.info(f"✅ {len(posts_data)}개 게시물 수집 완료")
            return posts_data[:num_posts]

except Exception as e:
        logger.error(f"❌ 스크래핑 실패: {str(e)}")
        return []

def analyze_with_gemini(posts_data):
          """Gemini로 트렌드 분석"""
    logger.info("🤖 Gemini로 트렌드 분석 중...")

    try:
                  if not posts_data:
                                    logger.error("분석할 게시물이 없습니다.")
            return None

        # 콘텐츠를 텍스트로 변환
        posts_text = "\n---\n".join([
                          f"작성자: {p['author']}\n좋아요: {p['likes']}\n내용: {p['text']}"
                          for p in posts_data
        ])

        prompt = f"""다음은 Threads의 최근 {len(posts_data)}개 인기 게시물입니다. 이 게시물들을 분석해서 현재의 주요 트렌드 10가지를 도출하고 정리해줘.

        ==== THREADS 게시물 데이터 ====
        {posts_text}

        ==== 분석 요청 ====
        위 게시물들을 분석해서 다음 형식으로 오늘의 주요 트렌드 TOP 10을 요약해줘:

        📊 *Threads 트렌드 TOP 10* ({datetime.now().strftime('%Y.%m.%d %H:%M UTC')})

        🔥 *1. 트렌드명*
        - 설명 (1-2줄): 이 트렌드와 관련된 주요 내용
        - 언급 수: 약 X개 게시물

        🔥 *2. 트렌드명*
        ...
        (이런 식으로 TOP 10까지)

        각 트렌드별로:
        - 트렌드의 핵심 내용
        - 관련 게시물 수
        - 주요 특징

        마지막에는:
        _분석 대상: 최신 {len(posts_data)}개 게시물 | 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC_"""

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt, safety_settings=[
                          {
                                                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                                                "threshold": "BLOCK_NONE",
                          },
                          {
                                                "category": "HARM_CATEGORY_HATE_SPEECH",
                                                "threshold": "BLOCK_NONE",
                          },
                          {
                                                "category": "HARM_CATEGORY_HARASSMENT",
                                                "threshold": "BLOCK_NONE",
                          },
                          {
                                                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                                                "threshold": "BLOCK_NONE",
                          },
        ])

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
    logger.info("=" * 60)
    logger.info("Threads 트렌드 분석 자동화 시작 (100개 게시물 분석)")
    logger.info("=" * 60)

    # 1. Threads 스크래핑 (100개)
    threads_data = scrape_threads_posts(num_posts=100)

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

    logger.info("=" * 60)
    logger.info("✅ 모든 작업 완료!")
    logger.info("=" * 60)

if __name__ == "__main__":
          main()
