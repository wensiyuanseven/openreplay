third-party.md 文件通常用于列出项目中使用的第三方库、工具和服务。这个文件可以帮助开发者和用户了解项目依赖的外部资源，并确保符合开源许可证和法律要求。该文件的常见内容包括第三方库的名称、版本、许可证类型以及使用目的。

third-party.md 文件的主要目的是提供透明度，确保项目的依赖关系清晰，并遵守相关的开源许可证要求。这对于开源项目尤为重要，因为开源社区高度重视许可证的合规性和透明度。

可以使用自动化工具来帮助收集依赖信息及其许可证。例如：
JavaScript/TypeScript:
  npx license-checker --json > dependencies.json
Python:
  pip-licenses --format=json > dependencies.json


## 许可证（截至 2024 年 3 月 28 日）
以下是 OpenReplay 软件中使用的依赖项列表。许可证可能会因版本而异，因此请保持此列表与您使用的每个新库保持同步更新。

## Licenses (as of Mars 28, 2024)

Below is the list of dependencies used in OpenReplay software. Licenses may change between versions, so please keep this
up to date with every new library you use.
| Library                    | License            | Scope          |
|----------------------------|--------------------|----------------|
| btcutil                    | IST                | Go             |
| confluent-kafka-go         | Apache2            | Go             |
| compress                   | Apache2            | Go             |
| uuid                       | BSD3               | Go             |
| mux                        | BSD3               | Go             |
| lib/pq                     | MIT                | Go             |
| pgconn                     | MIT                | Go             |
| pgx                        | MIT                | Go             |
| go-redis                   | BSD2               | Go             |
| pgerrcode                  | MIT                | Go             |
| pgzip                      | MIT                | Go             |
| maxminddb-golang           | IST                | Go             |
| realip                     | MIT                | Go             |
| uap-go                     | Apache2            | Go             |
| clickhouse-go              | MIT                | Go             |
| aws-sdk-go                 | Apache2            | Go             |
| logging                    | Apache2            | Go             |
| squirrel                   | MIT                | Go             |
| go-elasticsearch           | Apache2            | Go             |
| gorilla/websocket          | BSD2               | Go             |
| radix                      | MIT                | Go             |
| api                        | BSD3               | Go             |
| urllib3                    | MIT                | Python         |
| boto3                      | Apache2            | Python         |
| requests                   | Apache2            | Python         |
| pyjwt                      | MIT                | Python         |
| jsbeautifier               | MIT                | Python         |
| psycopg2-binary            | LGPL               | Python         |
| fastapi                    | MIT                | Python         |
| uvicorn                    | BSD                | Python         |
| python-decouple            | MIT                | Python         |
| pydantic                   | MIT                | Python         |
| apscheduler                | MIT                | Python         |
| python-multipart           | Apache             | Python         |
| elasticsearch-py           | Apache2            | Python         |
| jira                       | BSD2               | Python         |
| redis-py                   | MIT                | Python         |
| clickhouse-driver          | MIT                | Python         |
| python3-saml               | MIT                | Python         |
| kubernetes                 | Apache2            | Python         |
| chalice                    | Apache2            | Python         |
| pandas                     | BSD3               | Python         |
| numpy                      | BSD3               | Python         |
| scikit-learn               | BSD3               | Python         |
| apache-airflow             | Apache2            | Python         |
| airflow-code-editor        | Apache2            | Python         |
| mlflow                     | Apache2            | Python         |
| sqlalchemy                 | MIT                | Python         |
| pandas-redshift            | MIT                | Python         |
| confluent-kafka            | Apache2            | Python         |
| amplitude-js               | MIT                | JavaScript     |
| classnames                 | MIT                | JavaScript     |
| codemirror                 | MIT                | JavaScript     |
| copy-to-clipboard          | MIT                | JavaScript     |
| jsonwebtoken               | MIT                | JavaScript     |
| datamaps                   | MIT                | JavaScript     |
| microdiff                  | MIT                | JavaScript     |
| immutable                  | MIT                | JavaScript     |
| jsbi                       | Apache2            | JavaScript     |
| jshint                     | MIT                | JavaScript     |
| luxon                      | MIT                | JavaScript     |
| mobx                       | MIT                | JavaScript     |
| mobx-react-lite            | MIT                | JavaScript     |
| moment                     | MIT                | JavaScript     |
| moment-range               | Unlicense          | JavaScript     |
| optimal-select             | MIT                | JavaScript     |
| rc-time-picker             | MIT                | JavaScript     |
| snabbdom                   | MIT                | JavaScript     |
| react                      | MIT                | JavaScript     |
| react-circular-progressbar | MIT                | JavaScript     |
| react-codemirror2          | MIT                | JavaScript     |
| react-confirm              | MIT                | JavaScript     |
| react-datepicker           | MIT                | JavaScript     |
| react-daterange-picker     | Apache2            | JavaScript     |
| react-dnd                  | MIT                | JavaScript     |
| react-dnd-html5-backend    | MIT                | JavaScript     |
| react-dom                  | MIT                | JavaScript     |
| react-google-recaptcha     | MIT                | JavaScript     |
| react-json-view            | MIT                | JavaScript     |
| react-lazyload             | MIT                | JavaScript     |
| react-redux                | MIT                | JavaScript     |
| react-router               | MIT                | JavaScript     |
| react-router-dom           | MIT                | JavaScript     |
| react-stripe-elements      | MIT                | JavaScript     |
| react-toastify             | MIT                | JavaScript     |
| react-virtualized          | MIT                | JavaScript     |
| recharts                   | MIT                | JavaScript     |
| redux                      | MIT                | JavaScript     |
| redux-immutable            | BSD3               | JavaScript     |
| redux-thunk                | MIT                | JavaScript     |
| semantic-ui-react          | MIT                | JavaScript     |
| socket.io                  | MIT                | JavaScript     |
| socket.io-client           | MIT                | JavaScript     |
| uWebSockets.js             | Apache2            | JavaScript     |
| source-map                 | BSD3               | JavaScript     |
| aws-sdk                    | Apache2            | JavaScript     |
| serverless                 | MIT                | JavaScript     |
| peerjs                     | MIT                | JavaScript     |
| geoip-lite                 | Apache2            | JavaScript     |
| ua-parser-js               | MIT                | JavaScript     |
| express                    | MIT                | JavaScript     |
| jspdf                      | MIT                | JavaScript     |
| html-to-image              | MIT                | JavaScript     |
| kafka                      | Apache2            | Infrastructure |
| stern                      | Apache2            | Infrastructure |
| k9s                        | Apache2            | Infrastructure |
| minio                      | AGPLv3             | Infrastructure |
| postgreSQL                 | PostgreSQL License | Infrastructure |
| k3s                        | Apache2            | Infrastructure |
| nginx                      | BSD2               | Infrastructure |
| clickhouse                 | Apache2            | Infrastructure |
| redis                      | BSD3               | Infrastructure |
| yq                         | MIT                | Infrastructure |
| html2canvas                | MIT                | JavaScript     |
| eget                       | MIT                | Infrastructure |
| @medv/finder               | MIT                | JavaScript     |
| fflate                     | MIT                | JavaScript     |
| fzstd                      | MIT                | JavaScript     |
| prom-client                | Apache2            | JavaScript     |
| winston                    | MIT                | JavaScript     |
