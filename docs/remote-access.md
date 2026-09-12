# TinyFish 외부 점검과 ChatGPT Web 결과 조회

ipTIME DDNS가 HTTP만 제공하는 환경에서는 외부 브라우저 점검과 ChatGPT 연결을
같은 공개 주소로 처리하지 않는다.

- TinyFish는 임시로 공개한 합성 데이터 Streamlit 화면을 점검한다.
- ChatGPT Web은 인바운드 포트를 열지 않는 OpenAI Secure MCP Tunnel을 통해 완료
  보고서 전용 stdio MCP에 연결한다.
- 실제 세션 로그가 있는 `app.py`는 인증·암호화 없는 공용 HTTP에 노출하지 않는다.

## TinyFish용 합성 화면

외부 점검에는 실제 수집기·설정·사용자 DB를 쓰지 않는 `tests/browser_app.py`를 사용한다.
저장 동작은 프로세스의 임시 폴더에만 기록된다. 저장소 루트에서 다음과 같이 실행한다.

```bash
VERIFY_REQUEST_TOOLS=1 uv run --locked --group dev streamlit run tests/browser_app.py \
  --server.address=0.0.0.0 \
  --server.port=8501 \
  --server.headless=true \
  --server.fileWatcherType=none \
  --browser.serverAddress=ezcode92.iptime.org \
  --browser.serverPort=80
```

ipTIME에서는 서버 PC의 LAN 주소를 DHCP 고정 할당하고 TCP `외부 80 → 서버 LAN
주소 8501`로 포트포워딩한다. 공유기의 외부 관리 포트가 80이면 먼저 다른 포트로
옮기거나 외부 관리를 끈다. 서버 OS 방화벽도 TCP 8501을 허용해야 한다. 외부 8501을
그대로 쓸 때는 `--browser.serverPort=8501`로 바꾸고 URL에도 `:8501`을 붙인다.

다음 순서로 어느 구간이 막혔는지 분리한다.

```bash
curl --fail --show-error --max-time 10 http://127.0.0.1:8501/_stcore/health
curl --fail --show-error --max-time 10 http://SERVER_LAN_IP:8501/_stcore/health
curl --fail --show-error --max-time 10 http://ezcode92.iptime.org/_stcore/health
```

마지막 명령은 같은 와이파이가 아닌 휴대폰 데이터나 외부 호스트에서 실행한다. 앞의 두
요청만 성공하면 Streamlit이 아니라 DDNS, 포트포워딩, 호스트 방화벽 또는 통신사
CGNAT/인바운드 차단을 확인한다. 세 요청이 모두 `ok`를 반환한 뒤 TinyFish에
`http://ezcode92.iptime.org/` 전체 주소를 전달한다. 스킴을 생략하면 TinyFish가 HTTPS를
자동 선택할 수 있다.

TinyFish Browser API 세션 생성은 통상 10~30초가 걸릴 수 있으므로 API를 직접 호출할
때 HTTP 클라이언트 제한은 60초 이상, 세션의 `timeout_seconds`는 예를 들어 300초로 둔다.
점검이 끝나면 포트포워딩을 끄고 합성 화면 프로세스를 종료한다.

## ChatGPT Web에서 완료 보고서 읽기

### 파일로 확인

모든 ChatGPT 계정에서 쓸 수 있는 수동 경로는 앱의 `에이전트 분석` 화면에서
`분석 보고서 JSON`을 내려받아 ChatGPT 대화에 첨부하는 것이다. 이 파일에는 해당 분석
요청의 통계 스냅샷과 근거 목록이 포함되므로 업로드 전에 민감 정보를 확인한다.

### Secure MCP Tunnel로 실시간 확인

`mcp_server.py --scope results`는 같은 `analysis.sqlite3`에서 완료된 보고서만 읽는다.
제공 도구는 다음 두 개뿐이다.

- `list_analysis_reports`: 최신 완료 보고서의 ID, 목적, 요약과 항목 수
- `get_analysis_report`: 선택한 보고서와 실제로 참조한 근거

원본 로그 조회·분석 요청 생성·인수·완료 도구는 없으며 이벤트 근거의 로컬
`source_path`와 `record_key`도 결과에서 제거한다. 로컬에서 도구를 확인하려면 다음 명령을
MCP Inspector의 stdio 대상으로 사용할 수 있다.

```bash
uv run --locked python mcp_server.py --scope results
```

ChatGPT Web 연결은 OpenAI Platform에서 `tunnel_id`와 런타임 키를 만든 뒤, 저장소가 있는
호스트에서 `tunnel-client`가 위 stdio 명령을 실행하도록 구성한다. 키는 저장소 파일이나
명령 기록에 넣지 않는다.

```bash
export CONTROL_PLANE_API_KEY="<runtime-api-key>"

tunnel-client init \
  --sample sample_mcp_stdio_local \
  --profile agent-session-monitor-results \
  --tunnel-id <tunnel_id> \
  --mcp-command "uv --directory /home/ezcode/workspace/projects/agent-session-monitor run --locked python /home/ezcode/workspace/projects/agent-session-monitor/mcp_server.py --scope results"

tunnel-client doctor --profile agent-session-monitor-results --explain
tunnel-client run --profile agent-session-monitor-results
```

ChatGPT의 개발자 모드에서 새 앱을 만들고 연결 방식으로 `Tunnel`을 선택한 뒤 같은
`tunnel_id`를 고른다. 연결 후 “완료된 분석 보고서를 목록으로 보여줘”로 목록 도구를,
“이 job ID의 보고서와 근거를 함께 검토해줘”로 상세 도구를 확인한다. 개발자 모드와 터널
사용 가능 여부는 계정 및 워크스페이스 정책에 따라 달라질 수 있다.

Secure MCP Tunnel은 사설 개발 연결용이며 공개 플러그인 배포를 대신하지 않는다. 공개
배포에는 안정적으로 접근 가능한 HTTPS Streamable HTTP MCP 엔드포인트가 별도로 필요하므로,
HTTP 전용 ipTIME DDNS 주소를 ChatGPT MCP URL로 직접 등록할 수는 없다.

## 관련 문서

- [MCP 연결과 분석 흐름](mcp.md)
- [Streamlit 원격 배포](https://docs.streamlit.io/deploy/tutorials/docker)
- [TinyFish Browser API](https://docs.tinyfish.ai/browser-api/reference)
- [OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [ChatGPT에서 MCP 연결 테스트](https://developers.openai.com/plugins/deploy/connect-chatgpt)
