# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | ------: | --------: |
| api/\_\_init\_\_.py                                   |        0 |        0 |    100% |           |
| api/dependencies.py                                   |       12 |        0 |    100% |           |
| api/rate\_limit.py                                    |        3 |        0 |    100% |           |
| api/routes/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| api/routes/account\_routes.py                         |       31 |        0 |    100% |           |
| api/routes/analytics\_routes.py                       |       40 |        0 |    100% |           |
| api/routes/backtest\_routes.py                        |       41 |        1 |     98% |        72 |
| api/routes/crypto\_routes.py                          |       18 |        0 |    100% |           |
| api/routes/forex\_routes.py                           |        6 |        0 |    100% |           |
| api/routes/fx\_watch\_routes.py                       |       77 |        4 |     95% |     85-90 |
| api/routes/guru\_routes.py                            |      149 |        4 |     97% |226, 357, 605-606 |
| api/routes/holding\_routes.py                         |       98 |        4 |     96% |217-220, 275 |
| api/routes/networth\_routes.py                        |       47 |        3 |     94% |51, 161-162 |
| api/routes/persona\_routes.py                         |       37 |        0 |    100% |           |
| api/routes/preferences\_routes.py                     |       16 |        0 |    100% |           |
| api/routes/scan\_routes.py                            |       82 |        6 |     93% |51-52, 60-61, 150, 186 |
| api/routes/snapshot\_routes.py                        |       80 |        9 |     89% |37-38, 41-42, 56-57, 75-76, 116 |
| api/routes/stock\_routes.py                           |      162 |       44 |     73% |135-138, 151, 157-168, 176, 190, 254-255, 264-267, 287, 303, 309, 334-339, 351-353, 367-378, 390-392, 403-405, 418-420 |
| api/routes/telegram\_routes.py                        |       19 |        0 |    100% |           |
| api/routes/thesis\_routes.py                          |       19 |        0 |    100% |           |
| api/routes/transaction\_routes.py                     |       25 |        0 |    100% |           |
| api/schemas/\_\_init\_\_.py                           |       14 |        0 |    100% |           |
| api/schemas/account.py                                |       20 |        0 |    100% |           |
| api/schemas/analytics.py                              |       10 |        0 |    100% |           |
| api/schemas/backtest.py                               |        8 |        0 |    100% |           |
| api/schemas/common.py                                 |        7 |        0 |    100% |           |
| api/schemas/crypto.py                                 |        6 |        0 |    100% |           |
| api/schemas/fx\_watch.py                              |       24 |        0 |    100% |           |
| api/schemas/guru.py                                   |      108 |        0 |    100% |           |
| api/schemas/guru\_analytics.py                        |       24 |        0 |    100% |           |
| api/schemas/networth.py                               |       65 |        9 |     86% |39, 59-61, 67-74 |
| api/schemas/notification.py                           |       41 |        0 |    100% |           |
| api/schemas/portfolio.py                              |      120 |        0 |    100% |           |
| api/schemas/scan.py                                   |       87 |        0 |    100% |           |
| api/schemas/stock.py                                  |       59 |        1 |     98% |        78 |
| api/schemas/transaction.py                            |       33 |        0 |    100% |           |
| application/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| application/formatters.py                             |      106 |        8 |     92% |82-83, 122, 265, 267, 294-296 |
| application/guru/\_\_init\_\_.py                      |        4 |        0 |    100% |           |
| application/guru/backtest\_service.py                 |      109 |       16 |     85% |62, 72, 89, 92-97, 148, 200, 212-214, 235-236, 239, 244, 259-260 |
| application/guru/guru\_service.py                     |       47 |        2 |     96% |  103, 105 |
| application/guru/heatmap\_service.py                  |       83 |       17 |     80% |40, 55-56, 62-63, 66-67, 72-77, 98, 133, 141, 149 |
| application/guru/resonance\_service.py                |       95 |       12 |     87% |39, 71, 77-78, 81-82, 87-92 |
| application/messaging/\_\_init\_\_.py                 |        3 |        0 |    100% |           |
| application/messaging/notification\_service.py        |      247 |       15 |     94% |52-56, 61-66, 136, 357, 436-437 |
| application/messaging/telegram\_settings\_service.py  |       54 |        1 |     98% |        85 |
| application/messaging/webhook\_service.py             |      218 |       21 |     90% |60, 182-187, 223-228, 314-322, 387-388, 406-407, 567-569, 627-628 |
| application/portfolio/\_\_init\_\_.py                 |       15 |        0 |    100% |           |
| application/portfolio/account\_service.py             |       68 |        8 |     88% |104-105, 112-115, 132, 154 |
| application/portfolio/analytics\_service.py           |       27 |        0 |    100% |           |
| application/portfolio/crypto\_service.py              |       26 |        8 |     69% |15, 36, 49-53, 57 |
| application/portfolio/fx\_watch\_service.py           |      117 |        3 |     97% |151, 218, 384 |
| application/portfolio/holding\_service.py             |      107 |        2 |     98% |   57, 190 |
| application/portfolio/insight\_service.py             |       62 |        0 |    100% |           |
| application/portfolio/net\_worth\_service.py          |      215 |       37 |     83% |49-54, 139, 141, 143, 145, 147, 149, 151, 155, 208, 211-212, 231, 330, 373-384, 404, 429-438, 471-472, 487-488 |
| application/portfolio/rebalance\_service.py           |      488 |       59 |     88% |126-154, 165, 231-232, 240-241, 248-254, 337-338, 526, 661, 842, 997, 1059, 1089, 1093-1108, 1134, 1142-1143, 1220-1227, 1233-1236, 1289, 1296, 1319-1322 |
| application/portfolio/settlement\_service.py          |       69 |        9 |     87% |35, 45, 77, 108, 114, 125, 150-152 |
| application/portfolio/snapshot\_service.py            |      120 |        7 |     94% |197-198, 202, 205-209, 213 |
| application/portfolio/stress\_test\_service.py        |       39 |        0 |    100% |           |
| application/portfolio/transaction\_service.py         |       43 |        2 |     95% |     53-54 |
| application/scan/\_\_init\_\_.py                      |        4 |        0 |    100% |           |
| application/scan/backfill\_service.py                 |       77 |        8 |     90% |68-71, 82-84, 151-153 |
| application/scan/backtest\_service.py                 |       80 |        2 |     98% |   45, 149 |
| application/scan/prewarm\_service.py                  |      164 |       20 |     88% |53, 77-80, 146, 158-159, 336-352, 387-388, 413-414 |
| application/scan/scan\_service.py                     |      317 |       73 |     77% |81-84, 127-130, 208, 247, 256, 266, 286, 297, 307, 317, 340, 342, 344, 399-401, 451, 511-534, 539, 567, 575-576, 579, 620, 632-634, 649-650, 696-701, 734-746, 779-784, 789-797 |
| application/services.py                               |        9 |        0 |    100% |           |
| application/settings/\_\_init\_\_.py                  |        2 |        0 |    100% |           |
| application/settings/persona\_service.py              |       53 |        0 |    100% |           |
| application/settings/preferences\_service.py          |       42 |        3 |     93% |60, 64, 93 |
| application/stock/\_\_init\_\_.py                     |        2 |        0 |    100% |           |
| application/stock/filing\_service.py                  |      193 |        9 |     95% |170-177, 217-221, 298, 302, 375 |
| application/stock/stock\_service.py                   |      344 |       54 |     84% |311, 318-319, 345-349, 390-392, 503, 508, 591, 609-610, 617-618, 622-624, 631-635, 645-650, 701-714, 727-728, 733-734, 738-739, 795-802, 843-857 |
| domain/\_\_init\_\_.py                                |        0 |        0 |    100% |           |
| domain/analysis/\_\_init\_\_.py                       |        7 |        0 |    100% |           |
| domain/analysis/analysis.py                           |      264 |        0 |    100% |           |
| domain/analysis/backtest.py                           |      115 |        9 |     92% |91, 101, 122, 126, 136-137, 236, 242, 272 |
| domain/analysis/drawdown.py                           |       60 |        0 |    100% |           |
| domain/analysis/fx\_analysis.py                       |      197 |        5 |     97% |48, 190, 230, 235, 273 |
| domain/analysis/guru\_backtest.py                     |      136 |       12 |     91% |54, 75, 78, 111, 116, 130, 146, 151, 158, 171, 201, 240 |
| domain/analysis/risk\_metrics.py                      |       46 |        0 |    100% |           |
| domain/analysis/smart\_money.py                       |       27 |        1 |     96% |        35 |
| domain/constants.py                                   |        1 |        0 |    100% |           |
| domain/core/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| domain/core/constants.py                              |      330 |        0 |    100% |           |
| domain/core/entities.py                               |      226 |        4 |     98% |264-265, 277-278 |
| domain/core/enums.py                                  |       67 |        0 |    100% |           |
| domain/core/formatters.py                             |       38 |        0 |    100% |           |
| domain/core/protocols.py                              |        3 |        0 |    100% |           |
| domain/entities.py                                    |        1 |        0 |    100% |           |
| domain/enums.py                                       |        1 |        0 |    100% |           |
| domain/formatters.py                                  |        1 |        0 |    100% |           |
| domain/fx\_analysis.py                                |        1 |        0 |    100% |           |
| domain/portfolio/\_\_init\_\_.py                      |        5 |        0 |    100% |           |
| domain/portfolio/allocation.py                        |       22 |        0 |    100% |           |
| domain/portfolio/insights.py                          |       47 |        0 |    100% |           |
| domain/portfolio/rebalance.py                         |       41 |        0 |    100% |           |
| domain/portfolio/stress\_test.py                      |       40 |        0 |    100% |           |
| domain/portfolio/withdrawal.py                        |      154 |       10 |     94% |81, 95, 113, 117, 123, 127, 157, 236, 250, 280 |
| domain/protocols.py                                   |        1 |        0 |    100% |           |
| domain/rebalance.py                                   |        1 |        0 |    100% |           |
| domain/smart\_money.py                                |        1 |        0 |    100% |           |
| domain/stress\_test.py                                |        1 |        0 |    100% |           |
| domain/withdrawal.py                                  |        1 |        0 |    100% |           |
| infrastructure/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| infrastructure/crypto.py                              |        1 |        0 |    100% |           |
| infrastructure/database.py                            |      147 |       49 |     67% |37-46, 155-156, 165-169, 195-196, 207-217, 224-225, 229-230, 251-252, 270-271, 295-317, 343-344 |
| infrastructure/external/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| infrastructure/external/crypto.py                     |       38 |        3 |     92% |     80-82 |
| infrastructure/external/notification.py               |       96 |       20 |     79% |149-150, 164-166, 171-177, 189-208 |
| infrastructure/external/sec\_edgar.py                 |      188 |       38 |     80% |78-83, 104-105, 119, 125-129, 135-139, 212-214, 277-279, 315-316, 393-395, 419, 429-431, 439, 442, 448-449 |
| infrastructure/finmind\_adapter.py                    |        1 |        1 |      0% |         6 |
| infrastructure/jquants\_adapter.py                    |        1 |        0 |    100% |           |
| infrastructure/market\_data/\_\_init\_\_.py           |        2 |        0 |    100% |           |
| infrastructure/market\_data/crypto\_adapter.py        |      211 |      101 |     52% |84-89, 96, 102, 111-112, 123-127, 141-157, 165-166, 173-174, 185-188, 192-194, 200, 202, 211, 222-225, 235, 239, 241, 247, 251-252, 266, 270, 273, 285-293, 299-302, 306-323, 328-330, 335-372, 376-378 |
| infrastructure/market\_data/finmind\_adapter.py       |       55 |        2 |     96% |     55-56 |
| infrastructure/market\_data/jquants\_adapter.py       |       37 |        9 |     76% | 20, 26-34 |
| infrastructure/market\_data/market\_data.py           |     1187 |      427 |     64% |215, 379-380, 422-454, 520-528, 604, 615-617, 625-627, 665, 690-692, 707-708, 745, 776-798, 838, 903, 921, 936-938, 980-981, 1007-1012, 1069-1070, 1075-1082, 1090, 1111-1125, 1163-1164, 1190, 1206, 1245, 1263-1265, 1330-1345, 1365-1411, 1425-1456, 1461, 1477-1521, 1531-1549, 1615, 1629-1645, 1654, 1684-1689, 1706-1743, 1752-1762, 1770-1807, 1816-1826, 1831-1838, 1857, 1876, 1890-1892, 1919, 1956-1971, 2018, 2025, 2030, 2037, 2040-2042, 2066, 2077-2079, 2081-2085, 2101-2116, 2130-2177, 2191-2223, 2234-2240, 2256-2262, 2377, 2389, 2405-2430, 2532-2558, 2583-2591, 2603, 2624, 2659, 2755, 2803-2804, 2827, 2836, 2864-2869, 2874-2877, 2897-2902, 2904-2905 |
| infrastructure/market\_data/market\_data\_resolver.py |       73 |       23 |     68% |19-25, 43-44, 47-48, 54-55, 58-59, 62, 65, 68, 71, 121, 124, 127, 132 |
| infrastructure/market\_data\_resolver.py              |        1 |        1 |      0% |         6 |
| infrastructure/notification.py                        |        1 |        0 |    100% |           |
| infrastructure/persistence/\_\_init\_\_.py            |        1 |        0 |    100% |           |
| infrastructure/persistence/repositories.py            |      499 |       56 |     89% |63-71, 95-103, 129-142, 147-161, 173, 186-188, 356-359, 364-368, 385, 390-391, 480, 611, 1298-1301, 1320-1323, 1358-1361, 1383, 1385, 1387, 1389 |
| infrastructure/repositories.py                        |        1 |        0 |    100% |           |
| infrastructure/sec\_edgar.py                          |        1 |        0 |    100% |           |
| **TOTAL**                                             | **9613** | **1252** | **87%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/azusa152/Folio/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/azusa152/Folio/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fazusa152%2FFolio%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.