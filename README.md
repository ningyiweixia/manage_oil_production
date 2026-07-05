# 閲囨补浜屽巶浜曚笅浣滀笟绠＄悊绯荤粺

鍚庣閲囩敤 `FastAPI` + `SQLAlchemy 2.0` + `Pydantic v2` + `PostgreSQL 15 (JSONB)` + `Redis 7.4` + `Celery 5.4` + `JWT` + `Alembic`銆傚墠绔噰鐢?`Vue 3.5` + `Element Plus 2.9` + `ECharts 5.5` + `TypeScript 5.7` + `Vite 8.0`銆傜郴缁熸敮鎸?PostgreSQL/Redis/MinIO/A5/FPM 鐨勭敓浜ф帴鍏ワ紝涔熸敮鎸佹湰鍦?SQLite銆佸唴瀛樼紦瀛樺拰妯℃嫙澶栭儴绯荤粺鐨勯檷绾ц仈璋冦€?
## 蹇€熷叆鍙?
| 鍦烘櫙 | 鍦板潃/鍛戒护 |
|------|-----------|
| 鍓嶇寮€鍙戞湇鍔?| `http://127.0.0.1:5173` |
| 鍚庣 API | `http://127.0.0.1:8000/api/v1` |
| Swagger 鏂囨。 | `http://127.0.0.1:8000/docs` |
| 鍋ュ悍妫€鏌?| `http://127.0.0.1:8000/health` |
| 鍓嶇鏋勫缓 | `cd frontend && npm run build` |
| 鍚庣娴嬭瘯 | `python -m pytest` |
| 鍚庣璇硶妫€鏌?| `python -m compileall app alembic tests` |

榛樿绠＄悊鍛樿处鍙凤細

```json
{"username": "admin", "password": "ChangeMe_123!"}
```

> 棣栨鐧诲綍鍚庤绔嬪嵆淇敼榛樿瀵嗙爜锛屽苟鍦ㄧ敓浜х幆澧冩浛鎹?`.env` 涓殑鎵€鏈夐粯璁ゅ瘑閽ャ€?
## 妯″潡鎬昏

| 妯″潡 | 鐘舵€?| 璇存槑 |
|------|------|------|
| 绯荤粺搴曞眰鎼缓 | 鉁?宸插畬鎴?| PostgreSQL JSONB 妯″瀷銆丄lembic 杩佺Щ銆佺粺涓€寮傚父澶勭悊銆佹搷浣滄棩蹇椾腑闂翠欢銆丳rometheus 鎸囨爣鏆撮湶銆佹湰鍦伴檷绾ц繍琛?|
| 涓婁慨椤圭洰姹犵鐞?| 鉁?宸插畬鎴?| 椤圭洰姹?CRUD銆佸鏉?JSONB 鎺柦瀛楁銆佸鎵圭姸鎬佹満銆侀┏鍥為噸鎻愭櫤鑳借矾鐢便€佸垹闄ゅ綊妗ｃ€丒xcel 瀵煎叆瀵煎嚭 |
| RBAC 涓庣粺涓€璁よ瘉 | 鉁?宸插畬鎴?| JWT 鍙屼护鐗岋紙access + refresh锛夈€佺櫥鍑哄悐閿€銆佺敤鎴?瑙掕壊/鑿滃崟/鏉冮檺鍏?CRUD銆佺敤鎴风墿鐞嗗垹闄や繚鎶ゃ€佸姩鎬佽彍鍗曚笌鏉冮檺鎸夐挳瀹堝崼 |
| 鍓嶇涓氬姟鐣岄潰 | 鉁?宸插畬鎴?| Vue 3 + Element Plus 9 涓鍥俱€佸鎵瑰伐浣滃彴銆乄ebSocket 瀹炴椂寰呭姙鎻愰啋 |
| 鏁版嵁缁熻鍒嗘瀽 | 鉁?宸插畬鎴?| ECharts KPI 鍗＄墖銆佹煴鐘跺浘銆侀ゼ鍥俱€佺儹鍔涘浘銆佽秼鍔垮浘銆佸浘琛?PNG 瀵煎嚭銆丳andas DSL 鏌ヨ寮曟搸 |
| 鎵垮寘鍟嗚皟搴?| 鉁?宸插畬鎴?| 杩愬姏鎶ュ銆佷慨浜曡繍琛岃〃銆佸鎵瑰叆搴撹嚜鍔ㄥ缓杩愯琛ㄣ€佷紭鍏堟淳宸ユ帓搴忋€丷edis 鍒嗗竷寮忛攣闃查噸澶嶆淳宸ャ€佽繘搴﹁嚜鍔ㄦ帹杩?|
| A5 绯荤粺闆嗘垚 | 鉁?宸插畬鎴?| Celery 瀹氭椂鍚屾锛堟瘡 30 鍒嗛挓锛夈€佹墜鍔ㄨЕ鍙戙€丼SO 璺宠浆浠ょ墝銆丷ESTful 鍥炶皟锛圚MAC 绛惧悕锛夈€佸紓甯?鐗规畩宸ュ簭缁熻銆佽繍琛岃〃鍥炲啓 |
| 宸ョ▼璁捐绠＄悊 | 鉁?宸插畬鎴?| 瑙勫垯寮曟搸锛? 椤规牎楠岋級銆乸ython-docx/openpyxl 妯℃澘娓叉煋銆丮inIO 褰掓。銆佽嚜鍔ㄧ増鏈鐞?|
| 鐗╂枡绠＄悊涓庨厤閫?| 鉁?宸插畬鎴愶紙V4鏂板锛?| 鐗╂枡闇€姹?CRUD銆佺姸鎬佹祦杞紙寰呭鐞嗏啋宸插鏍糕啋宸茶鍒掆啋宸插嚭搴撯啋宸插埌鍦衡啋宸蹭娇鐢級銆佸紓甯告彁閱掋€佷笌淇簳杩愯琛ㄥ叧鑱?|
| 瀹屼簳鍒嗙被鍙拌处 | 鉁?宸插畬鎴愶紙V4鏂板锛?| 鎸夋帾鏂界被鍨嬪垎绫诲彴璐︺€佷慨鍓?淇悗鍏抽敭鏁版嵁璁板綍銆佸畬浜曟棩鏈?鏂藉伐闃熶紞绠＄悊銆佹帾鏂界被鍨嬪垎缁勭粺璁?|
| 椤圭洰姹犲瓧娈靛寮?| 鉁?宸插畬鎴愶紙V4鏂板锛?| 鏂板浜曞埆銆佸幙鍖恒€佸彂璧蜂汉銆佽仈绯荤數璇濄€佺収鐗囬檮浠剁瓑瀛楁锛屽畬鍠勪笟鍔℃暟鎹噰闆?|

## 椤圭洰缁撴瀯

```text
manage_oil_production/
鈹溾攢鈹€ main.py                          # FastAPI 搴旂敤鍏ュ彛
鈹溾攢鈹€ celery_app.py                    # Celery 鍒嗗竷寮忎换鍔￠槦鍒楅厤缃?鈹溾攢鈹€ requirements.txt                 # Python 渚濊禆
鈹溾攢鈹€ alembic.ini                      # 鏁版嵁搴撹縼绉婚厤缃?鈹溾攢鈹€ docker-compose.yml               # 瀹瑰櫒缂栨帓锛?1 鏈嶅姟锛?鈹溾攢鈹€ AGENTS.md                        # AI Agent 寮€鍙戜笂涓嬫枃鏂囨。
鈹溾攢鈹€ STARTUP_LOG.md                   # 鏈湴鍚姩楠岃瘉璁板綍
鈹溾攢鈹€ runtime-dashboard.html           # 杩愯鏃剁姸鎬佷华琛ㄧ洏
鈹?鈹溾攢鈹€ alembic/                         # 鏁版嵁搴撹縼绉?鈹?  鈹斺攢鈹€ versions/                    # 7 涓縼绉昏剼鏈?鈹?鈹溾攢鈹€ app/                             # 鍚庣搴旂敤
鈹?  鈹溾攢鈹€ api/
鈹?  鈹?  鈹溾攢鈹€ deps.py                  # 鏉冮檺渚濊禆娉ㄥ叆锛坓et_current_user / require_permission锛?鈹?  鈹?  鈹溾攢鈹€ ws.py                    # WebSocket 瀹℃壒閫氱煡锛圓pprovalConnectionManager锛?鈹?  鈹?  鈹斺攢鈹€ v1/
鈹?  鈹?      鈹溾攢鈹€ router.py            # API 璺敱鑱氬悎
鈹?  鈹?      鈹斺攢鈹€ endpoints/
鈹?  鈹?          鈹溾攢鈹€ auth.py          # 鐧诲綍/鍒锋柊/鐧诲嚭/褰撳墠鐢ㄦ埛
鈹?  鈹?          鈹溾攢鈹€ rbac.py          # 鐢ㄦ埛/瑙掕壊/鑿滃崟/鏉冮檺 CRUD + 鎿嶄綔鏃ュ織/瀹℃壒鏃ュ織
鈹?  鈹?          鈹溾攢鈹€ workover_project_pools.py  # 涓婁慨椤圭洰姹狅紙CRUD/鎻愪氦/瀹℃壒/Excel/鍒嗘瀽锛?鈹?  鈹?          鈹溾攢鈹€ contractors.py   # 鎵垮寘鍟嗚繍鍔?淇簳杩愯琛?娲惧伐/杩涘害
鈹?  鈹?          鈹溾攢鈹€ dictionaries.py  # 鏁版嵁瀛楀吀 CRUD
鈹?  鈹?          鈹溾攢鈹€ engineering.py   # 宸ョ▼璁捐鏂囨。锛堢敓鎴?涓嬭浇/瑙勫垯鏍￠獙锛?鈹?  鈹?          鈹斺攢鈹€ a5_integration.py # A5 闆嗘垚锛堝洖璋?SSO/鍚屾鐘舵€?鎵嬪姩瑙﹀彂锛?鈹?  鈹溾攢鈹€ core/
鈹?  鈹?  鈹溾攢鈹€ config.py                # 搴旂敤閰嶇疆锛圥ydantic Settings锛岀幆澧冨彉閲忛┍鍔級
鈹?  鈹?  鈹溾攢鈹€ exceptions.py            # 鍏ㄥ眬寮傚父澶勭悊锛圔usinessException + 澶氱被澶勭悊鍣級
鈹?  鈹?  鈹溾攢鈹€ middleware.py            # AuthMiddleware锛圝WT锛? OperationLogMiddleware锛堝璁★級
鈹?  鈹?  鈹溾攢鈹€ redis.py                 # Redis 缂撳瓨瀹㈡埛绔紙鑷姩闄嶇骇鍒板唴瀛樺瓧鍏革級
鈹?  鈹?  鈹溾攢鈹€ security.py              # JWT 绛惧彂/瑙ｇ爜/鍚婇攢锛坧bkdf2_sha256 + jose锛?鈹?  鈹?  鈹斺攢鈹€ status_codes.py          # 涓氬姟鐘舵€佺爜甯搁噺锛?0000/40001/40100/40300/40900/42900/50300/60001/60002锛?鈹?  鈹溾攢鈹€ crud/
鈹?  鈹?  鈹溾攢鈹€ rbac.py                  # 鐢ㄦ埛/瑙掕壊/鑿滃崟/鏉冮檺 CRUD 鏌ヨ
鈹?  鈹?  鈹溾攢鈹€ workover_project_pool.py # 椤圭洰姹?CRUD + 鐘舵€佹満 + ALLOWED_STATUS_TRANSITIONS
鈹?  鈹?  鈹溾攢鈹€ contractor.py            # 鎵垮寘鍟?CRUD + 淇簳杩愯琛?鈹?  鈹?  鈹斺攢鈹€ dictionary.py            # 鏁版嵁瀛楀吀 CRUD
鈹?  鈹溾攢鈹€ db/
鈹?  鈹?  鈹溾攢鈹€ base.py                  # ORM 鍩虹被锛圱imestampMixin锛? 绾︽潫鍛藉悕瑙勮寖
鈹?  鈹?  鈹溾攢鈹€ seed.py                  # 绉嶅瓙鏁版嵁锛?7 鑿滃崟/44 鏉冮檺/6 瑙掕壊/93 瀛楀吀/1 绠＄悊鍛橈級
鈹?  鈹?  鈹斺攢鈹€ session.py               # 鏁版嵁搴撳紩鎿?浼氳瘽宸ュ巶 + SQLite JSONB 鍏煎
鈹?  鈹溾攢鈹€ models/
鈹?  鈹?  鈹溾攢鈹€ rbac.py                  # User/Role/Menu/Permission/OperationLog + 3 涓棿琛?鈹?  鈹?  鈹溾攢鈹€ workover.py              # WorkoverProjectPool/ContractorCapacity/WorkoverOperationSheet
鈹?  鈹?  鈹溾攢鈹€ approval.py              # ApprovalLog锛坆efore/after JSONB 鏁版嵁蹇収锛?鈹?  鈹?  鈹溾攢鈹€ dictionary.py            # DataDictionary
鈹?  鈹?  鈹斺攢鈹€ engineering.py           # EngineeringDesignDoc
鈹?  鈹溾攢鈹€ schemas/                     # Pydantic v2 璇锋眰/鍝嶅簲妯″瀷锛坅uth/rbac/workover/contractor/...)
鈹?  鈹溾攢鈹€ services/                    # 涓氬姟閫昏緫鏈嶅姟灞傦紙15 涓湇鍔℃枃浠讹級
鈹?  鈹?  鈹溾攢鈹€ auth_service.py          # 璁よ瘉娴佺▼锛堢櫥褰?浠ょ墝鍒锋柊/鏉冮檺缂撳瓨/瑙掕壊鏋勫缓锛?鈹?  鈹?  鈹溾攢鈹€ rbac_service.py          # RBAC 涓氬姟閫昏緫
鈹?  鈹?  鈹溾攢鈹€ workover_analytics_service.py  # Pandas DSL 缁熻鍒嗘瀽寮曟搸
鈹?  鈹?  鈹溾攢鈹€ workover_project_pool_excel.py # Excel 瀵煎叆瀵煎嚭锛坧andas + openpyxl锛?鈹?  鈹?  鈹溾攢鈹€ dispatch_service.py      # Redis 鍒嗗竷寮忔淳宸ラ攣
鈹?  鈹?  鈹溾攢鈹€ notification_service.py  # WebSocket 瀹℃壒寰呭姙鎺ㄩ€?鈹?  鈹?  鈹溾攢鈹€ engineering_design_service.py  # 宸ョ▼璁捐鏂囨。鐢熸垚娴佹按绾?鈹?  鈹?  鈹溾攢鈹€ design_rule_engine.py    # 宸ョ▼璁捐瑙勫垯寮曟搸锛? 椤规牎楠岋級
鈹?  鈹?  鈹溾攢鈹€ template_renderer.py     # 妯℃澘娓叉煋锛坧ython-docx/openpyxl锛? MinIO 瀛樺偍
鈹?  鈹?  鈹溾攢鈹€ contractor_service.py    # 鎵垮寘鍟嗙姸鎬佺鐞?鈹?  鈹?  鈹溾攢鈹€ audit_service.py         # 瀹℃壒鏃ュ織鍐欏叆
鈹?  鈹?  鈹溾攢鈹€ dictionary_service.py    # 瀛楀吀鍊兼牎楠?鈹?  鈹?  鈹溾攢鈹€ a5_client.py             # A5 绯荤粺 HTTP 瀹㈡埛绔紙httpx + 瓒呮椂/閲嶈瘯锛?鈹?  鈹?  鈹溾攢鈹€ a5_auth_service.py       # A5 SSO 浠ょ墝鐢熸垚 + 鍥炶皟 HMAC 绛惧悕楠岃瘉
鈹?  鈹?  鈹溾攢鈹€ a5_sync_service.py       # A5 鏁版嵁鍚屾锛堟棩鎶?寮傚父/宸ュ簭锛? 鍛婅瑙﹀彂
鈹?  鈹?  鈹溾攢鈹€ a5_data_cleaner.py       # A5 鏁版嵁娓呮礂锛圥andas 鍘婚噸/鏍煎紡鍖?濉厖锛?鈹?  鈹?  鈹斺攢鈹€ fpm_client.py            # 闃插亸纾ㄧ郴缁?HTTP 瀹㈡埛绔紙鍚ā鎷熸ā寮忥級
鈹?  鈹溾攢鈹€ tasks/
鈹?  鈹?  鈹斺攢鈹€ a5_tasks.py              # Celery 瀹氭椂浠诲姟锛堟瘡 30 鍒嗛挓鍚屾 A5锛?鈹?  鈹斺攢鈹€ utils/
鈹?      鈹斺攢鈹€ jsonb.py                 # JSONB 鏌ヨ杈呭姪宸ュ叿
鈹?鈹溾攢鈹€ frontend/                        # Vue 3 + TypeScript 鍓嶇
鈹?  鈹斺攢鈹€ src/
鈹?      鈹溾攢鈹€ api/
鈹?      鈹?  鈹溾攢鈹€ http.ts              # Axios 瀹炰緥锛圔earer Token 鎷︽埅 + 401 閲嶅畾鍚?+ unwrap锛?鈹?      鈹?  鈹溾攢鈹€ auth.ts              # 璁よ瘉鎺ュ彛
鈹?      鈹?  鈹溾攢鈹€ workover.ts          # 椤圭洰姹?瀹℃壒鎺ュ彛锛堝惈婕旂ず妯″紡闄嶇骇锛?鈹?      鈹?  鈹溾攢鈹€ contractor.ts        # 鎵垮寘鍟嗚皟搴︽帴鍙?鈹?      鈹?  鈹溾攢鈹€ engineering.ts       # 宸ョ▼璁捐鎺ュ彛
鈹?      鈹?  鈹溾攢鈹€ dictionary.ts        # 鏁版嵁瀛楀吀鎺ュ彛
鈹?      鈹?  鈹溾攢鈹€ rbac.ts              # RBAC 绠＄悊鎺ュ彛
鈹?      鈹?  鈹斺攢鈹€ a5.ts                # A5 闆嗘垚鎺ュ彛
鈹?      鈹溾攢鈹€ composables/
鈹?      鈹?  鈹溾攢鈹€ useApprovalSocket.ts # WebSocket 绠＄悊锛堟寚鏁伴€€閬块噸杩?+ auth handshake锛?鈹?      鈹?  鈹斺攢鈹€ useProjectSync.ts    # 璺ㄧ粍浠朵簨浠舵€荤嚎
鈹?      鈹溾攢鈹€ router/
鈹?      鈹?  鈹斺攢鈹€ index.ts             # 14 璺敱 + JWT 瀵艰埅瀹堝崼
鈹?      鈹溾攢鈹€ styles/
鈹?      鈹?  鈹斺攢鈹€ main.css             # 鍏ㄥ眬鏍峰紡
鈹?      鈹溾攢鈹€ types/
鈹?      鈹?  鈹斺攢鈹€ workover.ts          # TypeScript 绫诲瀷瀹氫箟
鈹?      鈹溾攢鈹€ utils/
鈹?      鈹?  鈹斺攢鈹€ status.ts            # 瀹℃壒鐘舵€?娴佽浆/鏍囩宸ュ叿鍑芥暟
鈹?      鈹斺攢鈹€ views/
鈹?          鈹溾攢鈹€ LoginView.vue        # 鐧诲綍椤?鈹?          鈹溾攢鈹€ MainLayout.vue       # 涓诲竷灞€锛堝姩鎬?RBAC 渚ц竟鏍?+ 閫氱煡閾冮摏锛?鈹?          鈹溾攢鈹€ ApprovalWorkbench.vue # 瀹℃壒宸ヤ綔鍙帮紙鎼滅储/CRUD/鎵归噺鎻愪氦/瀹℃壒/WebSocket锛?鈹?          鈹溾攢鈹€ AnalyticsDashboard.vue # 缁熻鍒嗘瀽澶у睆锛圞PI/鍥捐〃/鐑姏鍥?瓒嬪娍/瀵煎嚭锛?鈹?          鈹溾攢鈹€ ContractorDispatchView.vue # 鎵垮寘鍟嗚繍鍔涗笌鏅鸿兘娲惧伐
鈹?          鈹溾攢鈹€ EngineeringDesignView.vue  # 宸ョ▼璁捐绠＄悊
鈹?          鈹溾攢鈹€ A5IntegrationView.vue # A5 绯荤粺闆嗘垚
鈹?          鈹溾攢鈹€ SystemAdminView.vue   # 绯荤粺绠＄悊锛堢敤鎴?瑙掕壊/鑿滃崟/鏉冮檺/鏁版嵁瀛楀吀/鏃ュ織 Tab锛?鈹?          鈹斺攢鈹€ DictionaryManageView.vue # 鏁版嵁瀛楀吀绠＄悊锛堝彲宓屽叆绯荤粺绠＄悊锛?鈹?鈹溾攢鈹€ deploy/                          # 閮ㄧ讲涓庡熀纭€璁炬柦
鈹?  鈹溾攢鈹€ docker/                      # 6 涓?Dockerfile锛堝闃舵鏋勫缓锛?鈹?  鈹溾攢鈹€ frontend-dist/               # 鍓嶇鏋勫缓浜х墿
鈹?  鈹溾攢鈹€ nginx/                       # Nginx 閰嶇疆锛圖MZ + SSL + 闄愭祦 + 瀹夊叏澶达級
鈹?  鈹溾攢鈹€ prometheus/                  # Prometheus 閰嶇疆 + 鍛婅瑙勫垯
鈹?  鈹溾攢鈹€ grafana/                     # Grafana 浠〃鏉块閰嶇疆
鈹?  鈹斺攢鈹€ scripts/
鈹?      鈹溾攢鈹€ deploy.sh                # Linux 涓€閿儴缃茶剼鏈?鈹?      鈹斺攢鈹€ deploy.ps1               # Windows 涓€閿儴缃茶剼鏈?鈹?鈹斺攢鈹€ tests/
    鈹斺攢鈹€ backend/
        鈹溾攢鈹€ test_database_unavailable.py  # 鏁版嵁搴撲笉鍙敤闄嶇骇娴嬭瘯
        鈹斺攢鈹€ test_a5_sync_service.py       # A5 鍚屾缁熻涓庡け璐ラ噸璇曟祴璇?```

## 鏈湴寮€鍙?
### 鍓嶇疆鏉′欢

- Python 3.12+
- Node.js 20+
- PostgreSQL 15锛堝彲閫夛紝鏃?PostgreSQL 鏃惰嚜鍔ㄤ娇鐢?SQLite锛?- Redis锛堝彲閫夛紝鏃?Redis 鏃惰嚜鍔ㄩ檷绾т负鍐呭瓨缂撳瓨锛?
### 鍚庣

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 鏁版嵁搴撹縼绉伙紙PostgreSQL 鎴?SQLite 鍧囧彲锛?alembic upgrade head
python -m app.db.seed

# 鍚姩鍚庣
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

璁块棶鍏ュ彛锛?
- 鍋ュ悍妫€鏌ワ細`GET http://127.0.0.1:8000/health`
- Swagger 鏂囨。锛歚http://127.0.0.1:8000/docs`
- Prometheus 鎸囨爣锛歚http://127.0.0.1:8000/metrics`

### 鍓嶇

```bash
cd frontend
npm install
npm run dev -- --port 5173
```

璁块棶鍏ュ彛锛?
- 鍓嶇寮€鍙戞湇鍔★細`http://127.0.0.1:5173`
- 榛樿浠ｇ悊鍚庣锛歚http://127.0.0.1:8000/api/v1`
- WebSocket 浠ｇ悊锛歚ws://127.0.0.1:8000/ws`

### 鏈湴杈呭姪鑴氭湰

浠撳簱鎻愪緵浜?Windows PowerShell 杈呭姪鑴氭湰锛?
```powershell
.\scripts\start-local-backend.ps1
.\scripts\check-local.ps1
.\scripts\visual-health.ps1
```

- `start-local-backend.ps1`锛氫互鏈湴鐜鍙橀噺鍚姩鍚庣鏈嶅姟
- `check-local.ps1`锛氭鏌ュ悗绔仴搴枫€佸墠绔〉闈㈠拰鍏抽敭浠ｇ悊閾捐矾
- `visual-health.ps1`锛氭墽琛屽熀纭€瑙嗚鍋ュ悍妫€鏌?
鏇磋缁嗙殑鏈湴鍚姩璁板綍瑙?`STARTUP_LOG.md`銆?
### Celery 寮傛浠诲姟

```bash
# 鍚姩 Celery Worker + Beat锛堝畾鏃朵换鍔★級
celery -A celery_app worker --loglevel=info --beat
```

- 瀹氭椂浠诲姟锛歚sync-a5-data-every-30min`锛堟瘡 30 鍒嗛挓鎷夊彇 A5 鏁版嵁锛?- 澶辫触閲嶈瘯锛氭渶澶?3 娆★紝闂撮殧 60 绉?- 杩炵画澶辫触 3 娆¤Е鍙戜紒涓氬井淇″憡璀?
## 鐜閰嶇疆

澶嶅埗 `.env.example` 涓?`.env` 骞舵牴鎹湰鍦扮幆澧冧慨鏀癸細

```env
DEBUG=true
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your-password>
POSTGRES_DB=manage_factory
REDIS_URL=redis://127.0.0.1:6379/0
JWT_SECRET_KEY=<generate-a-random-secret>
ADMIN_INITIAL_PASSWORD=ChangeMe_123!
ACCESS_TOKEN_EXPIRE_MINUTES=120
REFRESH_TOKEN_EXPIRE_MINUTES=10080
AUTH_WHITELIST=/docs,/docs/oauth2-redirect,/redoc,/openapi.json,/health,/metrics,/api/v1/auth/login,/api/v1/auth/refresh,/api/v1/auth/logout,/api/v1/a5/callback
CORS_ALLOW_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
A5_BASE_URL=
FPM_BASE_URL=
MINIO_ENDPOINT=127.0.0.1:9000
```

> `.env` 宸插姞鍏?`.gitignore`锛岀姝㈡彁浜ゃ€俁edis 涓嶅彲鐢ㄦ椂鑷姩闄嶇骇涓鸿繘绋嬪唴缂撳瓨锛涙湰鍦版湭閰嶇疆 A5/FPM/MinIO 鏃讹紝绯荤粺浼氫娇鐢ㄧ┖鏁版嵁銆佹ā鎷熷弬鏁板拰 `local_minio/` 鏈湴鏂囦欢鐩綍缁х画瀹屾垚鑱旇皟銆?
### 澶栭儴绯荤粺瀵规帴閰嶇疆

```env
# A5 绯荤粺闆嗘垚
A5_BASE_URL=           # A5 绯荤粺鍦板潃锛堢┖鍒欎娇鐢ㄦā鎷熼檷绾э級
A5_API_KEY=            # A5 API 瀵嗛挜
A5_API_SECRET=         # A5 API 瀵嗛挜锛圚MAC 绛惧悕锛?A5_IP_WHITELIST=       # IP 鐧藉悕鍗?ALERT_WEBHOOK_URL=     # 浼佷笟寰俊鍛婅 Webhook

# MinIO 瀵硅薄瀛樺偍
MINIO_ENDPOINT=127.0.0.1:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_ENGINEERING=engineering-designs
MINIO_BUCKET_TEMPLATES=design-templates

# 闃插亸纾ㄨ璁＄郴缁?FPM_BASE_URL=          # 闃插亸纾ㄧ郴缁熷湴鍧€锛堢┖鍒欎娇鐢ㄦā鎷熷弬鏁帮級
```

> 鐢熶骇/鑱旇皟鐜鎺ュ叆鐪熷疄绯荤粺鏃跺啀濉叆 `A5_BASE_URL` 鍜?`FPM_BASE_URL`銆侫5 绯荤粺鐨勫洖璋冭矾寰?`/api/v1/a5/callback` 宸插湪 `AUTH_WHITELIST` 涓厤閴存潈锛岀敱 HMAC 绛惧悕楠岃瘉淇濋殰瀹夊叏銆?
### 鏈湴闄嶇骇妯″紡

| 渚濊禆 | 涓嶅彲鐢ㄦ椂鐨勮涓?|
|------|---------------|
| PostgreSQL | 鑷姩浣跨敤 SQLite锛坄local_dev.db`锛夛紝JSONB 鈫?JSON 鍏煎閫傞厤 |
| Redis | 缂撳瓨鍜屽垎甯冨紡閿佸洖閫€鍒拌繘绋嬪唴瀛樺疄鐜?|
| MinIO | 宸ョ▼璁捐鏂囨。鍐欏叆 `local_minio/` 鏈湴鐩綍 |
| A5 绯荤粺 | 鍚屾浠诲姟杩斿洖绌烘暟鎹苟璁板綍鎴愬姛鐘舵€侊紝鍓嶇姝ｅ父灞曠ず |
| FPM 绯荤粺 | 宸ョ▼璁捐浣跨敤妯℃嫙闃插亸纾ㄥ弬鏁?|

## API 瑙勮寖

### 缁熶竴鍝嶅簲鏍煎紡

```json
{"code": 20000, "msg": "success", "data": {}}
```

### 涓氬姟鐘舵€佺爜

| 鐘舵€佺爜 | 鍚箟 | HTTP |
|--------|------|------|
| `20000` | 鎴愬姛 | 200 |
| `40001` | 鍙傛暟閿欒 | 400 |
| `40100` | 鐧诲綍澶辨晥 | 401 |
| `40300` | 瓒婃潈璁块棶 | 403 |
| `40900` | 涓氬姟鍐茬獊锛堝苟鍙戝啿绐侊級 | 409 |
| `42900` | 璇锋眰杩囦簬棰戠箒 | 429 |
| `50300` | 鏁版嵁搴撲笉鍙敤 | 503 |
| `60001` | A5 绯荤粺鑱斿姩澶辫触 | 502 |
| `60002` | 闃插亸纾ㄧ郴缁熻仈鍔ㄥけ璐?| 502 |

### API 鏍囧噯鐢熷懡鍛ㄦ湡锛? 姝ユ硶锛?
`璇锋眰鍙戣捣 鈫?韬唤璁よ瘉锛圓uthMiddleware锛夆啋 鍙傛暟鏍￠獙锛圥ydantic v2锛夆啋 浜嬪姟鎵ц 鈫?鎿嶄綔鐣欑棔锛圤perationLogMiddleware + approval_log 蹇収锛夆啋 缁撴灉杩斿洖`

## 璁よ瘉涓庢潈闄愶紙RBAC锛?
### 璁よ瘉鎺ュ彛

```text
POST /api/v1/auth/login      鐧诲綍锛岃繑鍥炵敤鎴蜂俊鎭€佹潈闄愭爲銆佽彍鍗曟爲鍜屽弻浠ょ墝
POST /api/v1/auth/refresh    鍒锋柊 access token
POST /api/v1/auth/logout     鐧诲嚭骞跺悐閿€ refresh token锛圧edis JTI 榛戝悕鍗曪級
GET  /api/v1/auth/me         褰撳墠鐢ㄦ埛淇℃伅
```

- JWT 鍙屼护鐗岋細access_token锛堥粯璁?120 鍒嗛挓锛? refresh_token锛堥粯璁?7 澶╋級
- 鐧诲綍闄愭祦锛氭瘡 IP 姣?5 鍒嗛挓鏈€澶?5 娆″皾璇?- 鐧诲嚭鍚婇攢锛氬熀浜?JTI 鐨?Redis 榛戝悕鍗曟満鍒?
### RBAC 绠＄悊鎺ュ彛

```text
GET    /api/v1/users                   鐢ㄦ埛鍒楄〃
POST   /api/v1/users                   鏂板鐢ㄦ埛
PUT    /api/v1/users/{user_id}         缂栬緫鐢ㄦ埛
PATCH  /api/v1/users/{user_id}/active  鍚仠鐢ㄦ埛
PATCH  /api/v1/users/{user_id}/roles   鍒嗛厤瑙掕壊
DELETE /api/v1/users/{user_id}         鍒犻櫎鐢ㄦ埛锛堢墿鐞嗗垹闄わ紝瓒呯骇绠＄悊鍛樼姝㈠垹闄わ級

GET    /api/v1/roles                   瑙掕壊鍒楄〃
POST   /api/v1/roles                   鏂板瑙掕壊
PUT    /api/v1/roles/{role_id}         缂栬緫瑙掕壊
PATCH  /api/v1/roles/{role_id}/menus        鍒嗛厤鑿滃崟
PATCH  /api/v1/roles/{role_id}/permissions  鍒嗛厤鏉冮檺
DELETE /api/v1/roles/{role_id}         鍒犻櫎瑙掕壊

GET    /api/v1/menus                   鑿滃崟鍒楄〃锛堟爲褰紝鏀寔鐖跺瓙宓屽锛?POST   /api/v1/menus                   鏂板鑿滃崟
PUT    /api/v1/menus/{menu_id}         缂栬緫鑿滃崟
DELETE /api/v1/menus/{menu_id}         鍒犻櫎鑿滃崟

GET    /api/v1/permissions             鏉冮檺鍒楄〃
POST   /api/v1/permissions             鏂板鏉冮檺
PUT    /api/v1/permissions/{perm_id}   缂栬緫鏉冮檺
DELETE /api/v1/permissions/{perm_id}   鍒犻櫎鏉冮檺

GET    /api/v1/operation-logs          鎿嶄綔鏃ュ織鏌ヨ
GET    /api/v1/approval-logs           瀹℃壒鏃ュ織鏌ヨ锛堥粯璁?100 鏉★紝鏈€澶?500 鏉★級
```

鍒犻櫎鐢ㄦ埛鏃讹紝绯荤粺浼氬厛娓呯悊鐢ㄦ埛瑙掕壊鍏崇郴锛屽苟灏嗗叧鑱斿鎵规棩蹇椼€侀」鐩垱寤轰汉瀛楁缃┖锛岄伩鍏嶅巻鍙插璁℃暟鎹洜澶栭敭绾︽潫琚骇鑱斿垹闄ゃ€?
### 鍐呯疆瑙掕壊锛圫eed Data锛?
| 瑙掕壊 | 缂栫爜 | 璇存槑 |
|------|------|------|
| 瓒呯骇绠＄悊鍛?| `super_admin` | 鍏ㄩ儴鏉冮檺 |
| 椤圭洰姹犵鐞嗗憳 | `project_pool_admin` | 椤圭洰姹?CRUD + 鎻愪氦绠＄悊 |
| 鍩哄眰褰曞叆鍛?| `base_entry_clerk` | 鍩哄眰鍗曚綅椤圭洰姹犳暟鎹綍鍏?|
| 涓氬姟瀹℃牳鍛?| `business_reviewer` | 鍦拌川/宸ヨ壓瀹℃牳 |
| 鎵垮寘鍟嗘搷浣滃憳 | `contractor_operator` | 杩愬姏鎶ュ |
| 杩愮淮绠＄悊鍛?| `ops_admin` | 绯荤粺鐩戞帶 + A5 闆嗘垚绠＄悊 |

### 鏁版嵁瀛楀吀

```text
GET    /api/v1/dictionaries/               瀛楀吀鍒楄〃锛堟敮鎸?dict_type 绛涢€夛級
POST   /api/v1/dictionaries/               鏂板瀛楀吀椤?PUT    /api/v1/dictionaries/{id}           缂栬緫瀛楀吀椤?PATCH  /api/v1/dictionaries/{id}/active    鍚仠瀛楀吀椤?DELETE /api/v1/dictionaries/{id}           鍒犻櫎瀛楀吀椤?```

瀛楀吀琛ㄧ淮鎶ゅ瓧鍏哥被鍨嬨€佹帾鏂界被鍨嬨€侀」鐩姸鎬併€佽繍琛岀姸鎬併€佸鎵瑰姩浣溿€佷笟鍔＄被鍨嬨€佺郴缁熻鑹层€佺郴缁熻彍鍗曘€佸閮ㄧ郴缁熺瓑鏋氫妇銆傛帴鍙ｅ眰閫氳繃 `ensure_dictionary_values` 鎸?`item_value` 寮哄埗鏍￠獙锛岀瀛愭暟鎹細鎶婂巻鍙蹭腑鏂囨帾鏂藉€艰縼绉讳负绋冲畾缂栫爜銆?
## 涓婁慨椤圭洰姹犵鐞?
### 瀹℃壒鐘舵€佹満

```
DRAFT 鈫?PENDING_GEOLOGY_VERIFY 鈫?PENDING_PROCESS_VERIFY 鈫?APPROVED 鈫?DISPATCHED
                 鈹?                       鈹?                 鈹斺攢鈹€ REJECTED 鈫愨攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?```

### 鐘舵€佽浆鎹㈣鍒?
| 褰撳墠鐘舵€?| 鍏佽杞崲鍒?|
|----------|-----------|
| `DRAFT` | `PENDING_GEOLOGY_VERIFY` |
| `PENDING_GEOLOGY_VERIFY` | `PENDING_PROCESS_VERIFY`, `REJECTED` |
| `PENDING_PROCESS_VERIFY` | `APPROVED`, `REJECTED` |
| `APPROVED` | `DISPATCHED` |
| `REJECTED` | `DRAFT`, `PENDING_GEOLOGY_VERIFY`, `PENDING_PROCESS_VERIFY` |
| `DISPATCHED` | 鏃?|

### 椹冲洖鏅鸿兘璺敱

浠庨┏鍥炵姸鎬侀噸鏂版彁鎶ユ椂锛岀郴缁熻嚜鍔ㄤ粠瀹℃壒鏃ュ織涓煡鎵鹃┏鍥炲墠鐨勫鎵硅妭鐐癸細

- 鍦ㄥ湴璐ㄦ牳瀹炶椹冲洖 鈫?閲嶆柊鎻愪氦鑷?*鍦拌川鏍稿疄**
- 鍦ㄥ伐鑹烘牳瀹炶椹冲洖 鈫?閲嶆柊鎻愪氦鑷?*宸ヨ壓鏍稿疄**

### 涓昏鎺ュ彛

```text
GET    /api/v1/workover-project-pools/                鍒楄〃锛堝垎椤点€佸鏉′欢绛涢€夛級
GET    /api/v1/workover-project-pools/{id}            璇︽儏
POST   /api/v1/workover-project-pools/                鏂板鑽夌
PUT    /api/v1/workover-project-pools/{id}            缂栬緫
DELETE /api/v1/workover-project-pools/{id}            鍒犻櫎褰掓。锛坕s_deleted=true锛屽垪琛ㄩ殣钘忥級
PATCH  /api/v1/workover-project-pools/submit          鎵归噺鎻愪氦鑷冲鎵?PATCH  /api/v1/workover-project-pools/{id}/status     瀹℃壒閫氳繃/椹冲洖/閲嶆柊鎻愭姤
POST   /api/v1/workover-project-pools/import          Excel 瀵煎叆锛圥andas 鎵归噺瑙ｆ瀽锛?GET    /api/v1/workover-project-pools/export/all      Excel 瀵煎嚭锛坆ase64锛?GET    /api/v1/workover-project-pools/analytics/summary  缁熻鍒嗘瀽鑱氬悎
```

### 绛涢€夊弬鏁?
| 鍙傛暟 | 璇存槑 |
|------|------|
| `page` / `page_size` | 鍒嗛〉 |
| `status` | 瀹℃壒鐘舵€?|
| `well_no` | 浜曞彿锛堟ā绯婂尮閰嶏級 |
| `block_name` | 鍖哄潡锛堟ā绯婂尮閰嶏級 |
| `measure_type` | 鎺柦绫诲瀷锛堝瓧鍏稿€肩簿纭尮閰嶏級 |

椤圭洰鍒楄〃杩斿洖 `rejected_from_status` 瀛楁锛屾爣鏄庨┏鍥為」鐩湪琚┏鍥炲墠鎵€澶勭殑瀹℃壒鑺傜偣锛屽墠绔嵁姝ゅ尯鍒嗐€屽湴璐ㄩ┏鍥炪€嶄笌銆屽伐鑹洪┏鍥炪€嶃€傞」鐩鎵归€氳繃鍚庤繘鍏モ€滃凡鍏ュ簱鈥濓紝绯荤粺鑷姩鍒涘缓瀵瑰簲淇簳杩愯琛紱娲惧伐鍚庨」鐩姸鎬佹帹杩涗负 `DISPATCHED`銆?
## 鎵垮寘鍟嗚皟搴?
### 鏅鸿兘娲惧伐鎺掑簭

娲惧伐鎺ュ彛涓ユ牸鎸変互涓嬭鍒欐帓搴忥紙鏂规寮哄埗瑕佹眰锛夛細
1. 瀹℃壒閫氳繃鏃堕棿鍗囧簭锛堝厛瀹℃壒鐨勪紭鍏堟淳宸ワ級
2. 浜ч噺浼樺厛绾ч檷搴忥紙楂樹紭鍏堢骇浼樺厛锛?
瀹℃壒閫氳繃鐨勯」鐩細鑷姩鐢熸垚涓€鏉?`WAITING_DISPATCH` 淇簳杩愯琛ㄣ€傝繍琛岃〃鍒楄〃鍜屽緟娲惧伐鍒楄〃鍔犺浇鏃朵細鍏滃簳鍚屾宸插叆搴撻」鐩紝閬垮厤婕忓缓杩愯琛ㄣ€?
### Redis 鍒嗗竷寮忛攣闃查噸

```
PATCH /api/v1/contractors/dispatch
```

- 閿?KEY锛歚dispatch:lock:{contractor_capacity_id}`
- TTL锛?0 绉掞紙闃叉閿侊級
- 鍔犻攣澶辫触杩斿洖 `40900` 骞跺彂鍐茬獊

### 鏂藉伐杩涘害鐘舵€佹満

```
WAITING_DISPATCH 鈫?DISPATCHED 鈫?WORKING 鈫?FINISHED
                        鈹?           鈹?                        鈹斺攢鈹€ CANCELED 鈫愨敇
```

杩涘害鍒拌揪 100% 鏃惰嚜鍔ㄦ帹杩涳細
- `DISPATCHED` 鈫?`WORKING`锛坄actual_start_at` 鑷姩濉叆锛?- `WORKING` 鈫?`FINISHED`锛坄actual_end_at` 鑷姩濉叆锛?
A5 鍥炶皟鎴栨棩鎶ュ悓姝ヤ細鍐欏叆杩愯琛ㄧ殑 `a5_status`銆乣a5_remark`銆乣last_a5_sync_at`锛屽苟鎸?A5 鐘舵€佸悓姝ユ柦宸ョ姸鎬併€佽繘搴﹀拰鎵垮寘鍟嗗彲鐢ㄧ姸鎬併€?
### 涓昏鎺ュ彛

```text
GET    /api/v1/contractors/                               鎵垮寘鍟嗚繍鍔涘垪琛紙鍒嗛〉锛?POST   /api/v1/contractors/                               鏂板杩愬姏鎶ュ锛堝惈 capability_tags锛?GET    /api/v1/contractors/{id}                           杩愬姏璇︽儏
PUT    /api/v1/contractors/{id}                           鏇存柊杩愬姏鎶ュ

GET    /api/v1/contractors/priority-sheets                寰呮淳宸ヤ紭鍏堥『搴忓垪琛?GET    /api/v1/contractors/operation-sheets/              淇簳杩愯琛ㄥ垪琛紙鍒嗛〉锛?POST   /api/v1/contractors/operation-sheets/              鍒涘缓淇簳杩愯琛?GET    /api/v1/contractors/operation-sheets/{id}          杩愯琛ㄨ鎯?PATCH  /api/v1/contractors/dispatch                       娲惧伐锛圧edis 鍒嗗竷寮忛攣锛?PATCH  /api/v1/contractors/operation-sheets/{id}/progress 鏇存柊鏂藉伐杩涘害
```

## A5 绯荤粺闆嗘垚

### 闆嗘垚鏋舵瀯

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹? SSO 璺宠浆锛堜富鍔級   鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹? 鏈郴缁?  鈹?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈫?鈹?A5 绯荤粺   鈹?鈹?         鈹?鈫愨攢鈹€鈹€ 鍥炶皟锛堣鍔級鈹€鈹€ 鈹?         鈹?鈹? Celery  鈹?鈹€鈹€鈹€ 瀹氭椂鎷夊彇锛堜富鍔級鈫?鈹?         鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?                   鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?```

### API 绾︽潫

- 鎵€鏈夐泦鎴愭帴鍙ｄ娇鐢?HTTPS + Token 韬唤鍙岄噸閴存潈
- 鍥炶皟鎺ュ彛 `/api/v1/a5/callback` 鍔犲叆 `AUTH_WHITELIST` 鍏?JWT 閴存潈锛岀敱 HMAC 绛惧悕楠岃瘉
- 閰嶇疆 IP 鐧藉悕鍗曡闂檺鍒?- 鍏ㄩ噺鎺ュ彛璋冪敤鑷姩钀藉湴鏃ュ織

### 涓昏鎺ュ彛

```text
POST  /api/v1/a5/callback                 鎺ユ敹 A5 宸ュ崟鐘舵€佸洖璋冿紙HMAC 绛惧悕楠岃瘉锛?POST  /api/v1/a5/sso-token                鐢熸垚 SSO 璺宠浆浠ょ墝锛圝WT锛? 鍒嗛挓鏈夋晥锛?GET   /api/v1/a5/sync/status              鏌ョ湅鏈€杩戜竴娆″悓姝ョ姸鎬侊紙鎴愬姛/澶辫触/杩涜涓?鏃犺褰曪級
GET   /api/v1/a5/analytics/summary        鏌ョ湅 A5 寮傚父鍜岀壒娈婂伐搴忕粺璁?POST  /api/v1/a5/sync/trigger             鎵嬪姩瑙﹀彂鍏ㄩ噺鏁版嵁鍚屾
```

### A5 鏁版嵁鍥炲啓涓庣粺璁?
- 宸ュ崟鍥炶皟鍜屾棩鎶ュ悓姝ョ粺涓€鍐欏叆淇簳杩愯琛紝淇濈暀 A5 鐘舵€併€佸娉ㄣ€佹渶杩戝悓姝ユ椂闂村拰鍘熷鍥炲啓蹇収
- A5 鐘舵€佷細褰掍竴鍖栦负鏈郴缁熻繍琛岃〃鐘舵€侊細涓嬪彂/瀹℃牳涓?鈫?`DISPATCHED`锛屾柦宸ヤ腑 鈫?`WORKING`锛屽姙缁?瀹屾垚 鈫?`FINISHED`锛岄┏鍥?閫€鍥?鈫?`WAITING_DISPATCH`锛屽叧闂?鍙栨秷 鈫?`CANCELED`
- 寮傚父鎯呭喌鍜岀壒娈婂伐搴忔寜鍚屾鏃ユ湡鍐欏叆 Redis 缂撳瓨锛岀粺璁℃帴鍙ｆ敮鎸?`start_date`銆乣end_date`銆乣category` 绛涢€?- 鍏ㄩ噺鍚屾鍖呭惈鏃ユ姤銆佸紓甯搞€佺壒娈婂伐搴忎笁閮ㄥ垎锛涗换涓€閮ㄥ垎澶辫触浼氳褰?`partial_failure` 骞舵姏鍑轰笟鍔″紓甯革紝浜ょ粰 Celery 閲嶈瘯閾捐矾澶勭悊

### Celery 瀹氭椂浠诲姟

- `sync-a5-data-every-30min`锛氭瘡 30 鍒嗛挓杞鎷夊彇 A5 绯荤粺鏁版嵁
- 鎷夊彇鍐呭锛氫綔涓氭棩鎶ャ€佹柦宸ュ紓甯搞€佸伐搴忚繘搴?- 鏁版嵁娓呮礂锛氬熀浜?Pandas 鍘婚噸銆佹棩鏈熸牸寮忓寲銆佺己澶卞€煎～鍏?- 澶辫触閲嶈瘯锛氭渶澶?3 娆★紝杩炵画 3 娆″け璐ヨЕ鍙戜紒涓氬井淇?Webhook 鍛婅

### SSO 璺宠浆娴佺▼

```text
鍓嶇鐐瑰嚮"璺宠浆A5" 鈫?POST /api/v1/a5/sso-token 鈫?鍚庣绛惧彂 JWT 涓存椂浠ょ墝
鈫?杩斿洖 redirect_url锛堝惈 token + well_no锛?鈫?鍓嶇璺宠浆 A5 绯荤粺
鈫?A5 楠岃瘉浠ょ墝鍚庡睍绀哄伐鍗曟搷浣滈〉闈?```

## 宸ョ▼璁捐绠＄悊

### 鏂囨。鐢熸垚娴佹按绾?
```
鑾峰彇椤圭洰淇℃伅 鈫?璋冪敤闃插亸纾ㄧ郴缁熻幏鍙栧弬鏁?鈫?瑙勫垯寮曟搸鏍￠獙锛? 椤癸級
鈫?鑷姩鐢熸垚鐗堟湰鍙?鈫?妯℃澘娓叉煋锛坧ython-docx / openpyxl锛?鈫?MinIO 褰掓。 鈫?鍐欏叆瀹¤鏃ュ織
```

### 瑙勫垯寮曟搸鏍￠獙椤?
| 瑙勫垯 | 璇存槑 |
|------|------|
| 鎶芥补鏈哄瀷鍙峰尮閰?| 浜曟繁 > 3000m 蹇呴』浣跨敤鐗瑰畾鍨嬪彿鎶芥补鏈?|
| 鎺柦鍐茬獊妫€娴?| 閰稿寲鍜屽啿鐮傛礂浜曚笉鑳藉悓宸ュ簭杩涜 |
| 鏂藉伐鍙傛暟鑼冨洿 | 鍘嬪姏 0鈥?00MPa锛屾俯搴?-50鈥?00掳C |
| 闃插亸纾ㄥ弬鏁板畬鏁存€?| 蹇呴』鍖呭惈 `casing_diameter`銆乣tubing_size`銆乣wear_level` |
| 闃插亸纾ㄤ弗閲嶇▼搴?| `wear_level=SEVERE` 鏃堕樆鏂敓鎴?|

### 鏂囨。鐗堟湰绠＄悊

- 鐗堟湰鍙锋牸寮忥細`v1`, `v2`, `v3` 鈥?鑷姩閫掑
- 鏁版嵁搴?`UniqueConstraint(well_no, version)` 淇濊瘉鐗堟湰鍞竴

### 涓昏鎺ュ彛

```text
GET    /api/v1/engineering-designs/                  宸ョ▼璁捐鏂囨。鍒楄〃锛堝垎椤碉級
POST   /api/v1/engineering-designs/generate          涓€閿敓鎴愬伐绋嬭璁℃枃妗?GET    /api/v1/engineering-designs/{id}              鏂囨。璇︽儏
GET    /api/v1/engineering-designs/{id}/download     鑾峰彇 MinIO 棰勭鍚嶄笅杞介摼鎺?DELETE /api/v1/engineering-designs/{id}              鍒犻櫎鏂囨。
POST   /api/v1/engineering-designs/check-rules       鎵嬪姩瑙﹀彂瑙勫垯鏍￠獙
```

## 鍓嶇鍔熻兘

### 瀹℃壒宸ヤ綔鍙?
- 椤圭洰姹犲垪琛細澶氭潯浠剁瓫閫夈€佸垎椤点€佷紭鍏堢骇杩涘害鏉°€佹帾鏂芥爣绛俱€佸鎵规祦姝ラ鏉?- 鎵归噺鎻愪氦锛氬嬀閫夎崏绋块」鐩紝涓€閿彁浜よ嚦鍦拌川鏍稿疄
- 瀹℃壒鎿嶄綔锛氶€氳繃锛堟祦杞埌涓嬩竴鑺傜偣锛屽鎵归€氳繃鍚庤繘鍏ュ凡鍏ュ簱骞惰嚜鍔ㄥ缓杩愯琛級銆侀┏鍥烇紙閫€鍥炰慨鏀癸級
- 閲嶆柊鎻愭姤锛氭牴鎹?`rejected_from_status` 鏅鸿兘璺敱鍒板湴璐ㄦ牳瀹炴垨宸ヨ壓鏍稿疄
- 鎺柦 JSONB 琛ㄥ崟锛氬姩鎬佸鍒犳帾鏂借锛屾帾鏂界被鍨嬩笅鎷変粠瀛楀吀 API 鍔犺浇锛屾彁浜ゅ墠鏍￠獙鎺柦绫诲瀷蹇呭～涓斾笉閲嶅
- WebSocket 瀹炴椂寰呭姙锛氶〉闈㈠姞杞藉悗鑷姩杩炴帴 `/ws/approval`锛屾敹鍒版帹閫佹椂寮圭獥鎻愰啋

### 缁熻鍒嗘瀽澶у睆

- KPI 鍗＄墖锛氶」鐩€绘暟銆佸緟瀹℃壒鏁般€佸鎵归€氳繃鐜囥€侀璁℃€昏垂鐢ㄣ€佸钩鍧囦紭鍏堢骇
- 瀹℃壒鐘舵€佹煴鐘跺浘
- 鎺柦绫诲瀷楗煎浘锛堟寜鏁版嵁瀛楀吀灞曠ず涓枃鍚嶇О锛?- 鍖哄潡 脳 鐘舵€佺儹鍔涘浘锛堣鐩栬崏绋裤€佸緟瀹°€佸凡鍏ュ簱銆佸凡娲惧伐銆佸凡椹冲洖锛?- 鏃ユ彁鎶ヨ秼鍔挎姌绾?鏌辩姸娣峰悎鍥?- 鍥捐〃涓€閿鍑?PNG + 鏁版嵁鎽樿鏂囨湰瀵煎嚭

### A5 闆嗘垚鍓嶇

- 鍚屾鐘舵€佸崱鐗囷細鏈€杩戝悓姝ユ椂闂淬€佸悓姝ョ粨鏋溿€佸綋鏃ュ悓姝ユ鏁般€佽繍琛屼腑鐘舵€?- 寮傚父鎯呭喌缁熻锛氬睍绀?A5 寮傚父鎬绘暟鍜屾寜寮傚父绫诲埆鑱氬悎鐨勫垪琛?- 鐗规畩宸ュ簭缁熻锛氬睍绀?A5 鐗规畩宸ュ簭鎬绘暟鍜屾寜宸ュ簭绫诲埆鑱氬悎鐨勫垪琛?- SSO 璺宠浆锛氳緭鍏ヤ簳鍙风敓鎴?5 鍒嗛挓鏈夋晥璺宠浆閾炬帴

### RBAC 鑿滃崟闆嗘垚

- 鐧诲綍鏃惰幏鍙栫敤鎴疯彍鍗曟爲锛坄menus`锛夊拰鏉冮檺鍒楄〃锛坄permissions`锛?- 渚ц竟鏍忚彍鍗曠敱鍚庣 RBAC 鏁版嵁鍔ㄦ€侀┍鍔紝鏀寔鐖跺瓙宓屽銆佸浘鏍囨槧灏勩€佷笉鍙鑿滃崟杩囨护
- 鎿嶄綔鎸夐挳鏍规嵁鐢ㄦ埛鏉冮檺鑷姩鏄剧ず/闅愯棌
- 褰撳悗绔?RBAC 鏁版嵁涓嶅彲鐢ㄦ椂锛岃嚜鍔ㄥ洖閫€涓洪潤鎬佽彍鍗?
### 绯荤粺绠＄悊宸ヤ綔鍙?
- 鐢ㄦ埛绠＄悊锛氭柊澧炵敤鎴锋椂鏍￠獙澶嶆潅瀵嗙爜锛岃鑹查€夋嫨鏀舵暃涓哄崟瑙掕壊鍒嗛厤锛岃秴绾х鐞嗗憳绂佹鍒犻櫎
- 瑙掕壊/鑿滃崟/鏉冮檺绠＄悊锛氭敮鎸?RBAC 璧勬簮缁存姢鍜岃鑹叉巿鏉?- 鏁版嵁瀛楀吀锛氬湪绯荤粺绠＄悊椤靛唴缁熶竴缁存姢锛屾敮鎸佺被鍨嬮€夋嫨銆佸惎鍋溿€佺紪杈戝拰鍒犻櫎
- 鏃ュ織瀹¤锛氭搷浣滄棩蹇楀拰瀹℃壒鏃ュ織鍒嗙鏌ヨ锛屼究浜庤拷韪郴缁熸搷浣滀笌涓氬姟娴佽浆

### 鏉冮檺鎸夐挳鏄犲皠

| 鎸夐挳 | 鎵€闇€鏉冮檺 |
|------|----------|
| 鏂板鎻愭姤 | `workover_project_pool:create` |
| 缂栬緫椤圭洰 | `workover_project_pool:update` |
| 鎵归噺鎻愪氦 | `workover_project_pool:submit` |
| 閫氳繃 / 椹冲洖 | `workover_project_pool:approve` |
| 鍒犻櫎椤圭洰 | `workover_project_pool:delete` |

### WebSocket 娑堟伅鏍煎紡

```json
{
  "title": "瀹℃壒寰呭姙鎻愰啋",
  "message": "CY2-136 宸叉彁浜よ嚦鍦拌川鏍稿疄",
  "node_code": "PENDING_GEOLOGY_VERIFY",
  "type": "info"
}
```

杩炴帴绠＄悊锛氭寚鏁伴€€閬胯嚜鍔ㄩ噸杩烇紙鏈€澶?6 娆★級锛宎uth handshake 鍗忚銆?
## Alembic 鏁版嵁搴撹縼绉?
```bash
alembic upgrade head           # 鍗囩骇鍒版渶鏂?alembic downgrade -1           # 鍥為€€涓€涓増鏈?alembic revision --autogenerate -m "鎻忚堪"
```

### 杩佺Щ鍘嗗彶

| 鐗堟湰 | 鏃ユ湡 | 鍐呭 |
|------|------|------|
| `20260531_0001` | 2026-05-31 | 鏍稿績搴曞眰琛?+ RBAC 浣撶郴 |
| `20260602_0002` | 2026-06-02 | 涓婁慨椤圭洰姹犳ā鍧?+ data_dictionary + 瀛楁閲嶅懡鍚?+ 绱㈠紩 |
| `20260604_0003` | 2026-06-04 | 绯荤粺鍩虹鏀拺涓?RBAC + sys_menu + sys_operation_log + 瀛楁鎵╁睍 |
| `20260616_0004` | 2026-06-16 | 瀹夊叏涓庢暟鎹畬鏁存€т慨澶嶏紙杩涘害 0-100 绾︽潫 + 绱㈠紩 + action 鏋氫妇鎵╁睍锛?|
| `20260629_0005` | 2026-06-29 | 鏀寔鐢ㄦ埛鐗╃悊鍒犻櫎锛屽鎵规棩蹇楁搷浣滀汉鍜岄」鐩垱寤轰汉澶栭敭鏀逛负 `ON DELETE SET NULL` |
| `150795c9dad6` | 2026-06-30 | 绉婚櫎椤圭洰姹?`VOIDED` 鐘舵€侊紝鍘嗗彶浣滃簾璁板綍褰掑苟涓洪€昏緫鍒犻櫎鏁版嵁 |
| `20260630_0006` | 2026-06-30 | 淇簳杩愯琛ㄦ柊澧?A5 鐘舵€併€佸娉ㄥ拰鏈€杩戝悓姝ユ椂闂村瓧娈?|

## 瀹瑰櫒鍖栭儴缃?
瀹屾暣 Docker Compose 缂栨帓锛?1 鏈嶅姟锛? 闅旂缃戠粶锛夛細

```bash
# 涓€閿儴缃?# Linux
bash deploy/scripts/deploy.sh

# Windows
.\deploy\scripts\deploy.ps1
```

### 鏈嶅姟娓呭崟

| 鏈嶅姟 | 绔彛 | 缃戠粶鍖哄煙 |
|------|------|----------|
| Nginx (DMZ) | 443 | dmz_net |
| Frontend (SPA) | 鈥?| app_net |
| Backend (FastAPI) | 8000 | app_net + db_net |
| PostgreSQL 15 | 5432 | db_net |
| Redis 7.4 | 6379 | db_net |
| MinIO | 9000/9001 | db_net |
| Prometheus | 鈥?| monitor_net |
| Grafana | 鈥?| monitor_net |
| cAdvisor | 鈥?| monitor_net |
| Node Exporter | 鈥?| monitor_net |

### 缃戠粶鍒嗗尯

```
dmz_net (鍓嶇鎺ュ叆鍩?  鈫? Nginx锛圚TTPS 缁堢粨 + HSTS + CSP + 闄愭祦 20 req/s + burst 40锛?app_net (搴旂敤閫昏緫鍩?  鈫? FastAPI + Vue3 鍓嶇 + Prometheus + Grafana + cAdvisor + Node Exporter
db_net  (鏍稿績鏁版嵁鍩?  鈫? PostgreSQL + Redis + MinIO锛堜弗绂佸閮ㄧ洿鎺ヨ闂級
monitor_net (鐩戞帶鍩?  鈫? Prometheus + Grafana + 鎸囨爣閲囬泦
```

### 璁块棶鍏ュ彛

| 鍏ュ彛 | 鍦板潃 |
|------|------|
| 搴旂敤棣栭〉 | `https://localhost/` |
| 鍚庣鍋ュ悍妫€鏌?| `https://localhost/health` |
| Grafana 鐩戞帶 | `https://localhost/grafana/` |
| Prometheus | `https://localhost/prometheus/` |

### 鐩戞帶鍛婅瑙勫垯

| 鍛婅 | 鏉′欢 |
|------|------|
| 鍚庣瀹曟満 | 鎸佺画 2 鍒嗛挓鏃犲搷搴?|
| API 楂樺欢杩?| p95 > 1s 鎸佺画 5 鍒嗛挓 |
| 纾佺洏绌洪棿涓嶈冻 | 鍙敤绌洪棿 < 15% |
| 瀹瑰櫒 CPU 杩囬珮 | 鎸佺画 5 鍒嗛挓 > 80% |

璇﹁ `deploy/README.md`銆?
## 瀹夊叏璇存槑

- `.env`銆乣.local/`銆佹棩蹇椼€佽櫄鎷熺幆澧冦€佺紦瀛樻枃浠跺凡鍔犲叆 `.gitignore`
- 鎵€鏈夋煡璇娇鐢ㄥ弬鏁板寲锛岀姝㈣８ SQL 鎷兼帴
- 楂樺嵄鎿嶄綔锛堢紪杈?鍒犻櫎/鎻愭姤/瀹℃壒/娲惧伐/鐢熸垚鏂囨。锛夎嚜鍔ㄥ啓鍏?`approval_log` 瀹¤鏃ュ織锛屽惈鍙樻洿鍓嶅悗 JSONB 鏁版嵁蹇収
- JWT 鍏ㄥ眬閴存潈锛圓uthMiddleware锛? 璺敱绾?RBAC 鏉冮檺鏍￠獙锛坄require_permission` 渚濊禆娉ㄥ叆锛?- Redis JTI 榛戝悕鍗曞疄鐜颁护鐗屽悐閿€锛堜富鍔ㄧ櫥鍑哄嵆鏃跺け鏁堬級
- 鐧诲綍鎺ュ彛鍐呭瓨婊戝姩绐楀彛闄愭祦锛堟瘡 IP 姣?5 鍒嗛挓 5 娆★級
- 鎿嶄綔鏃ュ織璁板綍鐢ㄦ埛銆両P銆佹柟娉曘€佽矾寰勩€佹潈闄愭爣璇嗐€佽繑鍥炵爜
- A5 鍥炶皟鎺ュ彛 HMAC 绛惧悕楠岃瘉
- 鐢熶骇鐜 CSP 鐢?Nginx 娉ㄥ叆锛圚STS + X-Frame-Options + XSS-Protection锛?- 绂佹鎻愪氦 `frontend/src/**/*.js` / `*.js.map`锛堝凡鍔犲叆 `.gitignore`锛?
## 楠岃瘉璁板綍

鏈€杩戜竴娆℃枃妗ｄ笌鎻愪氦鍓嶆鏌ワ細**2026-06-30**

- 鉁?`pip install -r requirements.txt`
- 鉁?`alembic upgrade head`
- 鉁?`python -m app.db.seed`
- 鉁?鐧诲綍 / 鍒锋柊 / 鐧诲嚭 / 褰撳墠鐢ㄦ埛
- 鉁?鐢ㄦ埛 / 瑙掕壊 / 鑿滃崟 / 鏉冮檺 CRUD + 鎿嶄綔鏃ュ織
- 鉁?鏁版嵁瀛楀吀 CRUD + 鍚仠 + 鍒犻櫎
- 鉁?椤圭洰姹?CRUD + 鎻愪氦 + 瀹℃壒 + 椹冲洖 + 閲嶆柊鎻愭姤
- 鉁?椤圭洰姹犲垹闄ゅ綊妗?+ 绉婚櫎 `VOIDED` 鐘舵€?- 鉁?鏅鸿兘璺敱锛堝湴璐ㄩ┏鍥?鈫?鍦拌川閲嶆彁锛屽伐鑹洪┏鍥?鈫?宸ヨ壓閲嶆彁锛?- 鉁?鎿嶄綔鏃ュ織鑷姩鍐欏叆锛堝惈 before/after JSONB 蹇収锛?- 鉁?WebSocket 瀹℃壒寰呭姙鎺ㄩ€侊紙鍚?auth handshake + 鎸囨暟閫€閬块噸杩烇級
- 鉁?Excel 瀵煎叆瀵煎嚭锛圥andas 瑙ｆ瀽 + 鍏紡娑堟瘨锛?- 鉁?缁熻鍒嗘瀽 API锛圥andas DSL 寮曟搸锛?- 鉁?`npm install && npm run build`
- 鉁?`vue-tsc --noEmit` TypeScript 绫诲瀷妫€鏌ラ浂閿欒
- 鉁?Vue 3 鍓嶇鏋勫缓浜х墿杈撳嚭鍒?`deploy/frontend-dist/`
- 鉁?RBAC 鑿滃崟鍔ㄦ€佹覆鏌?+ 鏉冮檺鎸夐挳瀹堝崼
- 鉁?椹冲洖閲嶆彁鏅鸿兘璺敱锛堝墠绔娇鐢?`rejected_from_status`锛?- 鉁?鎵垮寘鍟嗚繍鍔涙姤澶?CRUD锛堝惈 capability_tags JSONB锛?- 鉁?淇簳杩愯琛?CRUD + 寰呮淳宸ヤ紭鍏堟帓搴忥紙approved_at + production_priority锛?- 鉁?瀹℃壒閫氳繃椤圭洰鑷姩鍒涘缓淇簳杩愯琛?- 鉁?Redis 鍒嗗竷寮忛攣闃查噸澶嶆淳宸ワ紙TTL 30s + 鑷姩閲婃斁锛?- 鉁?鏂藉伐杩涘害鏇存柊 + 鐘舵€佽嚜鍔ㄦ帹杩涳紙DISPATCHED 鈫?WORKING 鈫?FINISHED锛?- 鉁?A5 SSO 鍗曠偣鐧诲綍浠ょ墝鐢熸垚锛圝WT + 5 鍒嗛挓鏈夋晥鏈燂級
- 鉁?A5 RESTful 鍥炶皟鎺ユ敹锛圚MAC 绛惧悕楠岃瘉锛? 宸ュ崟鐘舵€佸悓姝?- 鉁?A5 鏁版嵁娓呮礂寮曟搸锛圥andas 鍘婚噸 / 鏃ユ湡鏍煎紡鍖?/ 缂哄け鍊煎～鍏咃級
- 鉁?A5 寮傚父/鐗规畩宸ュ簭缁熻缂撳瓨涓庢煡璇?- 鉁?A5 鍥炶皟/鏃ユ姤鍚屾鍐欏叆杩愯琛ㄧ姸鎬併€佸娉ㄥ拰鏈€杩戝悓姝ユ椂闂?- 鉁?Celery 瀹氭椂浠诲姟姣?30 鍒嗛挓鍚屾 A5 鏁版嵁锛堝惈 3 娆￠噸璇?+ 鍛婅锛?- 鉁?闃插亸纾ㄧ郴缁?HTTP 瀹㈡埛绔紙鍚湰鍦版ā鎷熸ā寮忥級
- 鉁?宸ョ▼璁捐瑙勫垯寮曟搸锛? 椤规牎楠岃鍒欙級
- 鉁?python-docx Word 鏂囨。妯℃澘娓叉煋
- 鉁?openpyxl Excel 鎶ヨ〃娓叉煋
- 鉁?MinIO 瀵硅薄瀛樺偍褰掓。锛堣嚜鍔ㄧ増鏈彿 v1/v2/v3鈥︼級
- 鉁?宸ョ▼璁捐鏂囨。 CRUD + 棰勭鍚嶄笅杞介摼鎺?- 鉁?鏈湴鏃?A5/FPM/MinIO 鏃堕檷绾ц仈璋冮€氳繃
- 鉁?绯荤粺绠＄悊鍓嶇锛氱敤鎴枫€佽鑹层€佽彍鍗曘€佹潈闄愩€佹暟鎹瓧鍏搞€佹搷浣滄棩蹇楀叆鍙ｉ€愰〉楠岃瘉閫氳繃
- 鉁?鐢ㄦ埛鐗╃悊鍒犻櫎娴佺▼锛氳秴绾х鐞嗗憳淇濇姢锛屽鎵规棩蹇楁搷浣滀汉鍜岄」鐩垱寤轰汉缃┖
- 鉁?`python -m pytest`
- 鉁?`POSTGRES_PASSWORD=dummy JWT_SECRET_KEY=dummy-secret ADMIN_INITIAL_PASSWORD='ChangeMe_123!' python -m compileall -q app main.py celery_app.py`

## 鏈湴杩愯鏃朵华琛ㄧ洏

椤圭洰鏍圭洰褰曠殑 `runtime-dashboard.html` 鎻愪緵浜嗘湰鍦拌繍琛屾椂鐘舵€佸彲瑙嗗寲闈㈡澘锛屽彲鐩磋鏌ョ湅锛?- 鏁版嵁搴撹繛鎺ョ姸鎬佷笌鐗堟湰
- Redis 杩炴帴鐘舵€?- Alembic 杩佺Щ鐘舵€?- API 绔偣鍋ュ悍妫€鏌?- 鍓嶇鏋勫缓鐘舵€?
浣跨敤鏂瑰紡锛氬惎鍔ㄥ悗绔悗锛屾祻瑙堝櫒鎵撳紑 `runtime-dashboard.html` 鍗冲彲鏌ョ湅瀹炴椂鐘舵€併€?