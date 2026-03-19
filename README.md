# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | ------: | --------: |
| api/\_\_init\_\_.py                                   |        0 |        0 |    100% |           |
| api/dependencies.py                                   |       12 |        0 |    100% |           |
| api/rate\_limit.py                                    |        3 |        0 |    100% |           |
| api/routes/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| api/routes/account\_routes.py                         |       47 |        0 |    100% |           |
| api/routes/analytics\_routes.py                       |       40 |        0 |    100% |           |
| api/routes/backtest\_routes.py                        |       41 |        1 |     98% |        72 |
| api/routes/crypto\_routes.py                          |       18 |        0 |    100% |           |
| api/routes/forex\_routes.py                           |        6 |        0 |    100% |           |
| api/routes/fx\_watch\_routes.py                       |       78 |        4 |     95% |     86-91 |
| api/routes/guru\_routes.py                            |      149 |        4 |     97% |226, 357, 605-606 |
| api/routes/holding\_routes.py                         |       63 |        3 |     95% |   106-109 |
| api/routes/persona\_routes.py                         |       37 |        0 |    100% |           |
| api/routes/preferences\_routes.py                     |       16 |        0 |    100% |           |
| api/routes/scan\_routes.py                            |       82 |        6 |     93% |51-52, 60-61, 150, 186 |
| api/routes/snapshot\_routes.py                        |       80 |        9 |     89% |37-38, 41-42, 56-57, 75-76, 116 |
| api/routes/stock\_routes.py                           |      170 |       32 |     81% |143-146, 159, 176, 204, 268-269, 278-281, 301, 320, 329, 358-363, 375-377, 391-402, 414-416, 427-429, 442-444 |
| api/routes/telegram\_routes.py                        |       19 |        0 |    100% |           |
| api/routes/thesis\_routes.py                          |       19 |        0 |    100% |           |
| api/routes/transaction\_routes.py                     |       43 |        0 |    100% |           |
| api/routes/wrapper\_routes.py                         |      111 |        2 |     98% |  260, 318 |
| api/schemas/\_\_init\_\_.py                           |       14 |        0 |    100% |           |
| api/schemas/account.py                                |       27 |        0 |    100% |           |
| api/schemas/analytics.py                              |       10 |        0 |    100% |           |
| api/schemas/backtest.py                               |        8 |        0 |    100% |           |
| api/schemas/common.py                                 |        8 |        0 |    100% |           |
| api/schemas/crypto.py                                 |        6 |        0 |    100% |           |
| api/schemas/fx\_watch.py                              |       48 |        1 |     98% |        69 |
| api/schemas/guru.py                                   |      108 |        0 |    100% |           |
| api/schemas/guru\_analytics.py                        |       24 |        0 |    100% |           |
| api/schemas/notification.py                           |       42 |        0 |    100% |           |
| api/schemas/portfolio.py                              |      104 |        0 |    100% |           |
| api/schemas/scan.py                                   |       88 |        0 |    100% |           |
| api/schemas/stock.py                                  |       82 |        1 |     99% |        80 |
| api/schemas/transaction.py                            |       73 |        1 |     99% |        64 |
| api/schemas/wrapper.py                                |       35 |        0 |    100% |           |
| application/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| application/formatters.py                             |      106 |        8 |     92% |82-83, 122, 265, 267, 294-296 |
| application/guru/\_\_init\_\_.py                      |        4 |        0 |    100% |           |
| application/guru/backtest\_service.py                 |      109 |       16 |     85% |62, 72, 89, 92-97, 148, 200, 212-214, 235-236, 239, 244, 259-260 |
| application/guru/guru\_service.py                     |       47 |        2 |     96% |  103, 105 |
| application/guru/heatmap\_service.py                  |       83 |       17 |     80% |40, 55-56, 62-63, 66-67, 72-77, 98, 133, 141, 149 |
| application/guru/resonance\_service.py                |      102 |       13 |     87% |45, 87-88, 91-92, 97-102, 113-114 |
| application/messaging/\_\_init\_\_.py                 |        3 |        0 |    100% |           |
| application/messaging/notification\_service.py        |      247 |       15 |     94% |52-56, 61-66, 136, 357, 436-437 |
| application/messaging/telegram\_settings\_service.py  |       54 |        1 |     98% |        85 |
| application/messaging/webhook\_service.py             |      257 |       17 |     93% |71, 202-207, 245-250, 339-347, 399, 416-417, 750-751 |
| application/portfolio/\_\_init\_\_.py                 |       13 |        0 |    100% |           |
| application/portfolio/account\_service.py             |      124 |        8 |     94% |76, 78, 150-154, 168, 231, 250, 272 |
| application/portfolio/analytics\_service.py           |       27 |        0 |    100% |           |
| application/portfolio/crypto\_service.py              |       26 |        8 |     69% |15, 36, 49-53, 57 |
| application/portfolio/eligibility\_service.py         |       63 |        1 |     98% |       206 |
| application/portfolio/eligible\_sync\_service.py      |      224 |       55 |     75% |40, 68, 102, 112, 150, 152, 190, 196, 211-213, 215, 235, 252, 265-273, 284-288, 297-312, 317-324, 330-333, 341-349 |
| application/portfolio/fx\_watch\_service.py           |      123 |        3 |     98% |163, 230, 400 |
| application/portfolio/holding\_service.py             |       63 |        1 |     98% |       125 |
| application/portfolio/insight\_service.py             |       62 |        0 |    100% |           |
| application/portfolio/nav\_sync\_service.py           |      138 |       24 |     83% |69-70, 85-86, 88, 94-95, 120-123, 146, 151-153, 210-211, 219-220, 224-228 |
| application/portfolio/pricing\_service.py             |       33 |        8 |     76% |32, 52-57, 59-61, 63 |
| application/portfolio/rebalance\_service.py           |      635 |       75 |     88% |156-184, 191, 195, 198-199, 203-208, 218, 298, 312-313, 344, 379, 384-390, 398-399, 406-412, 499-500, 662, 676-677, 869, 996, 1065-1067, 1199, 1381, 1443, 1473, 1485-1513, 1539, 1547-1548, 1633-1636, 1692, 1699, 1722-1725 |
| application/portfolio/routing\_service.py             |      155 |       40 |     74% |50-54, 77, 80, 91, 97-98, 103-106, 110, 124-141, 155, 171, 270, 285, 298, 309, 315 |
| application/portfolio/settlement\_service.py          |      264 |       30 |     89% |76, 86, 184, 225, 304, 315, 326, 341, 358-370, 398, 456-457, 463, 471, 480, 483, 494-495, 556, 559, 598, 638-639 |
| application/portfolio/snapshot\_service.py            |      120 |        7 |     94% |197-198, 202, 205-209, 213 |
| application/portfolio/stress\_test\_service.py        |       39 |        0 |    100% |           |
| application/portfolio/transaction\_service.py         |      140 |       15 |     89% |89-90, 106-107, 156, 182, 285-298 |
| application/portfolio/wrapper\_service.py             |       56 |        2 |     96% |   96, 129 |
| application/scan/\_\_init\_\_.py                      |        4 |        0 |    100% |           |
| application/scan/backfill\_service.py                 |       77 |        8 |     90% |68-71, 82-84, 151-153 |
| application/scan/backtest\_service.py                 |       80 |        2 |     98% |   45, 149 |
| application/scan/prewarm\_service.py                  |      211 |       29 |     86% |58, 82-85, 157, 169-170, 371-387, 422-423, 454-455, 486, 491-499 |
| application/scan/scan\_service.py                     |      351 |       80 |     77% |88-91, 134-137, 166-168, 193, 225, 264, 273, 283, 303, 314, 324, 334, 357, 359, 361, 416-418, 468, 528-551, 556, 584, 592-593, 596, 637, 649-651, 666-667, 724, 738-745, 779-791, 824-829, 834-842 |
| application/services.py                               |        9 |        0 |    100% |           |
| application/settings/\_\_init\_\_.py                  |        2 |        0 |    100% |           |
| application/settings/persona\_service.py              |       53 |        0 |    100% |           |
| application/settings/preferences\_service.py          |       42 |        3 |     93% |60, 64, 93 |
| application/stock/\_\_init\_\_.py                     |        2 |        0 |    100% |           |
| application/stock/filing\_service.py                  |      193 |        9 |     95% |170-177, 217-221, 298, 302, 375 |
| application/stock/stock\_service.py                   |      501 |       72 |     86% |142, 153, 242, 282, 461, 468-469, 495-499, 540-542, 653, 658, 666, 747, 767-768, 775-776, 780-782, 789-793, 803-808, 820-824, 844, 869, 877-883, 926-939, 955-956, 961-962, 967-968, 1025-1032, 1069, 1119-1133 |
| domain/\_\_init\_\_.py                                |        0 |        0 |    100% |           |
| domain/analysis/\_\_init\_\_.py                       |        7 |        0 |    100% |           |
| domain/analysis/analysis.py                           |      264 |        0 |    100% |           |
| domain/analysis/backtest.py                           |      115 |        9 |     92% |91, 101, 122, 126, 136-137, 236, 242, 272 |
| domain/analysis/drawdown.py                           |       60 |        0 |    100% |           |
| domain/analysis/fx\_analysis.py                       |      223 |        9 |     96% |48, 194, 234, 239, 277, 422, 493, 499-500 |
| domain/analysis/guru\_backtest.py                     |      136 |       12 |     91% |54, 75, 78, 111, 116, 130, 146, 151, 158, 171, 201, 240 |
| domain/analysis/risk\_metrics.py                      |       46 |        0 |    100% |           |
| domain/analysis/smart\_money.py                       |       27 |        1 |     96% |        35 |
| domain/constants.py                                   |        1 |        0 |    100% |           |
| domain/core/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| domain/core/constants.py                              |      330 |        0 |    100% |           |
| domain/core/entities.py                               |      244 |        4 |     98% |417-418, 430-431 |
| domain/core/enums.py                                  |       94 |        0 |    100% |           |
| domain/core/formatters.py                             |       38 |        0 |    100% |           |
| domain/core/protocols.py                              |        3 |        0 |    100% |           |
| domain/entities.py                                    |        1 |        0 |    100% |           |
| domain/enums.py                                       |        1 |        0 |    100% |           |
| domain/formatters.py                                  |        1 |        0 |    100% |           |
| domain/fx\_analysis.py                                |        1 |        0 |    100% |           |
| domain/portfolio/\_\_init\_\_.py                      |       10 |        0 |    100% |           |
| domain/portfolio/allocation.py                        |       24 |        0 |    100% |           |
| domain/portfolio/asset\_location.py                   |      180 |        7 |     96% |173, 183, 246, 297, 307, 312, 333 |
| domain/portfolio/detax.py                             |       45 |        1 |     98% |        62 |
| domain/portfolio/eligibility.py                       |       39 |        2 |     95% |   53, 104 |
| domain/portfolio/insights.py                          |       47 |        0 |    100% |           |
| domain/portfolio/rebalance.py                         |       41 |        0 |    100% |           |
| domain/portfolio/routing.py                           |       34 |        3 |     91% |28, 47, 57 |
| domain/portfolio/stress\_test.py                      |       40 |        0 |    100% |           |
| domain/portfolio/tax\_wrapper.py                      |       66 |        1 |     98% |        69 |
| domain/portfolio/withdrawal.py                        |      164 |       10 |     94% |97, 111, 129, 133, 139, 143, 243, 268, 282, 312 |
| domain/protocols.py                                   |        1 |        0 |    100% |           |
| domain/rebalance.py                                   |        1 |        0 |    100% |           |
| domain/smart\_money.py                                |        1 |        0 |    100% |           |
| domain/stress\_test.py                                |        1 |        0 |    100% |           |
| domain/withdrawal.py                                  |        1 |        0 |    100% |           |
| infrastructure/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| infrastructure/cache.py                               |       71 |        6 |     92% |44, 46, 48, 99, 111-113 |
| infrastructure/crypto.py                              |        1 |        0 |    100% |           |
| infrastructure/database.py                            |      181 |       58 |     68% |38-47, 245-246, 285-286, 297-307, 314-315, 319-320, 341-342, 360-361, 382-383, 407-429, 442-455, 483-484 |
| infrastructure/external/\_\_init\_\_.py               |        0 |        0 |    100% |           |
| infrastructure/external/crypto.py                     |       38 |        3 |     92% |     80-82 |
| infrastructure/external/eligible\_fund\_parser.py     |      163 |       26 |     84% |40, 43, 46-47, 64, 98-102, 122, 127-128, 139, 147, 153-154, 159, 162, 196, 215, 220, 224, 299-301 |
| infrastructure/external/notification.py               |       96 |       20 |     79% |149-150, 164-166, 171-177, 189-208 |
| infrastructure/external/sec\_edgar.py                 |      188 |       38 |     80% |78-83, 104-105, 119, 125-129, 135-139, 212-214, 277-279, 315-316, 393-395, 419, 429-431, 439, 442, 448-449 |
| infrastructure/finmind\_adapter.py                    |        1 |        1 |      0% |         6 |
| infrastructure/jquants\_adapter.py                    |        1 |        0 |    100% |           |
| infrastructure/market\_data/\_\_init\_\_.py           |        2 |        0 |    100% |           |
| infrastructure/market\_data/crypto\_adapter.py        |      211 |      101 |     52% |84-89, 96, 102, 111-112, 123-127, 141-157, 165-166, 173-174, 185-188, 192-194, 200, 202, 211, 222-225, 235, 239, 241, 247, 251-252, 266, 270, 273, 285-293, 299-302, 306-323, 328-330, 335-372, 376-378 |
| infrastructure/market\_data/finmind\_adapter.py       |       55 |        2 |     96% |     55-56 |
| infrastructure/market\_data/jquants\_adapter.py       |       37 |        9 |     76% | 20, 26-34 |
| infrastructure/market\_data/market\_data.py           |     1297 |      456 |     65% |230, 394-395, 437-469, 535-543, 619, 630-632, 640-642, 679-687, 709-711, 726-727, 764, 807, 922, 940, 955-957, 999-1000, 1026-1031, 1088-1089, 1097, 1099-1101, 1130-1144, 1182-1183, 1209, 1225, 1264, 1282-1284, 1352-1385, 1405-1451, 1465-1496, 1501, 1517-1561, 1571-1589, 1652-1685, 1693-1696, 1713, 1724-1729, 1746-1783, 1792-1802, 1810-1847, 1856-1866, 1871-1878, 1897, 1916, 1930-1932, 1959, 1996-2011, 2058, 2065, 2070, 2077, 2080-2082, 2106, 2117-2119, 2121-2125, 2141-2156, 2170-2217, 2231-2263, 2274-2280, 2296-2302, 2417, 2429, 2445-2470, 2572-2598, 2623-2631, 2643, 2664, 2699, 2797, 2845-2846, 2862-2864, 2873, 2888, 2906-2908, 2917, 2932, 2954-2955, 2973-2974, 2997, 3006, 3034-3039, 3044-3047, 3067-3072, 3074-3075 |
| infrastructure/market\_data/market\_data\_resolver.py |       73 |       23 |     68% |19-25, 43-44, 47-48, 54-55, 58-59, 62, 65, 68, 71, 121, 124, 127, 132 |
| infrastructure/market\_data/toushin\_adapter.py       |       79 |        9 |     89% |41, 47, 50-51, 92, 96-97, 108, 114 |
| infrastructure/market\_data/toushin\_lib\_adapter.py  |      111 |        4 |     96% |75-77, 139 |
| infrastructure/market\_data\_resolver.py              |        1 |        1 |      0% |         6 |
| infrastructure/notification.py                        |        1 |        0 |    100% |           |
| infrastructure/persistence/\_\_init\_\_.py            |        1 |        0 |    100% |           |
| infrastructure/persistence/repositories.py            |      780 |      137 |     82% |74-82, 106-114, 140-153, 158-172, 184, 367-370, 375-379, 396, 401-402, 491, 622, 1254, 1268, 1300, 1350-1353, 1358-1359, 1364-1369, 1397-1400, 1419-1422, 1457-1460, 1484, 1486, 1488, 1556-1564, 1576, 1625, 1641, 1651, 1669, 1733, 1779, 1823-1840, 1843-1847, 1852, 1867-1870, 1874, 1943, 1960-1961, 2020-2051, 2072-2077, 2094, 2100-2103, 2108-2109 |
| infrastructure/repositories.py                        |        1 |        0 |    100% |           |
| infrastructure/sec\_edgar.py                          |        1 |        0 |    100% |           |
| **TOTAL**                                             | **12230** | **1586** | **87%** |           |


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