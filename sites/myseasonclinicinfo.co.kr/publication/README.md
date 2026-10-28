# Approved manuscript publication

Project: appgprj_6abcc6b8701881919cd1b85b40e49868
Public site: https://myseasonclinicinfo.co.kr
User approved all 430 supplied manuscripts for publication without rewriting.

Each day in Asia/Seoul, open the latest Site source using the Sites hosting skill before making changes. Run `python publish.py` then `python verify_publication.py`. The first script releases up to 5 unpublished manuscripts per hourly slot (09:00–18:59 Asia/Seoul) and enforces a total cap of 50 per local date, including retries. It regenerates the static site from the durable ledger in state.json. Do not change start_date or publication dates, regenerate manuscripts, or publish the entire queue at once. If none remain, disable the recurring automation.

Use the normal Sites source workflow, save archive and deploy publicly to the SAME project. Preserve the current domain, access, images, original six representative posts, and exact user-supplied titles/body text. All article pages include a visible 대구필러 anchor to http://myseasonclinicinfo.co.kr. Source-only approved.json must never be copied into dist. Only dist is public.

If publishing fails after the source ledger is saved, retry deploying that source version before releasing another batch. Compare live and latest source versions via Sites tools. Never advance a new date's batch while the previous saved batch remains undeployed. Report failures accurately. Same-day script retries do not consume another batch.

First batch: October 1, 2026, 50 manuscripts. From October 2, publish 5 per hour from 09:00 through 18:00 Asia/Seoul (10 runs, 50 per day). Never catch up missed runs by publishing more than 5 in one run or one hour. The final day contains 30 manuscripts across 6 runs. This schedule ends after all 430 have been published.
