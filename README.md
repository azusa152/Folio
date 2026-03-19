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
| api/routes/dividend\_routes.py                        |       30 |        2 |     93% |    70, 84 |
| api/routes/forex\_routes.py                           |        6 |        0 |    100% |           |
| api/routes/fx\_watch\_routes.py                       |       78 |        4 |     95% |     86-91 |
| api/routes/guru\_routes.py                            |      149 |        4 |     97% |226, 357, 605-606 |
| api/routes/holding\_routes.py                         |       84 |        5 |     94% |176-179, 205-206 |
| api/routes/persona\_routes.py                         |       37 |        0 |    100% |           |
| api/routes/preferences\_routes.py                     |       16 |        0 |    100% |           |
| api/routes/scan\_routes.py                            |       82 |        6 |     93% |51-52, 60-61, 150, 186 |
| api/routes/snapshot\_routes.py                        |       80 |        9 |     89% |37-38, 41-42, 56-57, 75-76, 116 |
| api/routes/stock\_routes.py                           |      170 |       32 |     81% |143-146, 159, 176, 204, 268-269, 278-281, 301, 320, 329, 358-363, 375-377, 391-402, 414-416, 427-429, 442-444 |
| api/routes/stock\_split\_routes.py                    |       30 |        2 |     93% |    68, 82 |
| api/routes/telegram\_routes.py                        |       19 |        0 |    100% |           |
| api/routes/thesis\_routes.py                          |       19 |        0 |    100% |           |
| api/routes/transaction\_routes.py                     |       43 |        0 |    100% |           |
| api/routes/wrapper\_routes.py                         |      111 |        2 |     98% |  260, 318 |
| api/schemas/\_\_init\_\_.py                           |       16 |        0 |    100% |           |
| api/schemas/account.py                                |       27 |        0 |    100% |           |
| api/schemas/analytics.py                              |       10 |        0 |    100% |           |
| api/schemas/backtest.py                               |        8 |        0 |    100% |           |
| api/schemas/common.py                                 |        8 |        0 |    100% |           |
| api/schemas/crypto.py                                 |        6 |        0 |    100% |           |
| api/schemas/dividend.py                               |       13 |        0 |    100% |           |
| api/schemas/fx\_watch.py                              |       48 |        1 |     98% |        69 |
| api/schemas/guru.py                                   |      108 |        0 |    100% |           |
| api/schemas/guru\_analytics.py                        |       24 |        0 |    100% |           |
| api/schemas/notification.py                           |       42 |        0 |    100% |           |
| api/schemas/portfolio.py                              |      104 |        0 |    100% |           |
| api/schemas/scan.py                                   |       88 |        0 |    100% |           |
| api/schemas/stock.py                                  |       82 |        1 |     99% |        80 |
| api/schemas/stock\_split.py                           |       14 |        0 |    100% |           |
| api/schemas/transaction.py                            |       95 |        6 |     94% |64, 78, 143-145, 147 |
| api/schemas/wrapper.py                                |       35 |        0 |    100% |           |
| application/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| application/formatters.py                             |      106 |        8 |     92% |82-83, 122, 265, 267, 294-296 |
| application/guru/\_\_init\_\_.py                      |        4 |        0 |    100% |           |
| application/guru/backtest\_service.py                 |      109 |       16 |     85% |62, 72, 89, 92-97, 148, 200, 212-214, 235-236, 239, 244, 259-260 |
| application/guru/guru\_service.py                     |       47 |        2 |     96% |  103, 105 |
| application/guru/heatmap\_service.py                  |       83 |       17 |     80% |40, 55-56, 62-63, 66-67, 72-77, 98, 133, 141, 149 |
| application/guru/resonance\_service.py                |      102 |       13 |     87% |45, 87-88, 91-92, 97-102, 113-114 |
| application/messaging/\_\_init\_\_.py                 |        3 |        0 |    100% |           |
| application/messaging/notification\_service.py        |      254 |       19 |     93% |52-56, 61-66, 136, 357, 374-377, 446-447 |
| application/messaging/telegram\_settings\_service.py  |       54 |        1 |     98% |        85 |
| application/messaging/webhook\_service.py             |      308 |       39 |     87% |81, 212-217, 255-260, 349-357, 409, 426-427, 531-548, 557-575, 609-619, 655-665, 932-933 |
| application/portfolio/\_\_init\_\_.py                 |       16 |        0 |    100% |           |
| application/portfolio/account\_service.py             |      124 |        8 |     94% |76, 78, 150-154, 168, 231, 250, 272 |
| application/portfolio/alert\_ack\_service.py          |       24 |        0 |    100% |           |
| application/portfolio/analytics\_service.py           |       27 |        0 |    100% |           |
| application/portfolio/crypto\_service.py              |       26 |        8 |     69% |15, 36, 49-53, 57 |
| application/portfolio/dividend\_service.py            |      146 |       38 |     74% |64, 72, 80, 93-97, 122, 136-137, 161, 211-220, 229-252, 285, 313, 318, 320, 323-324, 330-331, 333 |
| application/portfolio/drift\_alert\_service.py        |       80 |       22 |     72% |54-55, 66, 69-70, 89-90, 98, 105, 128-130, 161-177, 180 |
| application/portfolio/eligibility\_service.py         |       63 |        1 |     98% |       206 |
| application/portfolio/eligible\_sync\_service.py      |      224 |       55 |     75% |40, 68, 102, 112, 150, 152, 190, 196, 211-213, 215, 235, 252, 265-273, 284-288, 297-312, 317-324, 330-333, 341-349 |
| application/portfolio/fx\_watch\_service.py           |      123 |        3 |     98% |163, 230, 400 |
| application/portfolio/holding\_service.py             |       63 |        1 |     98% |       125 |
| application/portfolio/insight\_service.py             |       62 |        0 |    100% |           |
| application/portfolio/nav\_sync\_service.py           |      138 |       24 |     83% |69-70, 85-86, 88, 94-95, 120-123, 146, 151-153, 210-211, 219-220, 224-228 |
| application/portfolio/pricing\_service.py             |       33 |        8 |     76% |32, 52-57, 59-61, 63 |
| application/portfolio/rebalance\_service.py           |      666 |       88 |     87% |165-193, 200, 204, 207-208, 212-217, 227, 307, 321-322, 353, 388, 393-399, 407-408, 415-421, 508-509, 671, 685-686, 878, 1005, 1074-1076, 1120-1121, 1135, 1142-1143, 1169, 1173-1185, 1188, 1282, 1464, 1526, 1556, 1568-1596, 1622, 1630-1631, 1716-1719, 1775, 1782, 1805-1808 |
| application/portfolio/routing\_service.py             |      155 |       40 |     74% |50-54, 77, 80, 91, 97-98, 103-106, 110, 124-141, 155, 171, 270, 285, 298, 309, 315 |
| application/portfolio/settlement\_service.py          |      274 |       26 |     91% |79, 89, 187, 228, 312, 323, 334, 349, 367, 369-378, 420, 482, 490, 499, 502, 513-514, 575, 578, 622, 662-663 |
| application/portfolio/snapshot\_service.py            |      120 |        7 |     94% |197-198, 202, 205-209, 213 |
| application/portfolio/stock\_split\_service.py        |      159 |       30 |     81% |65, 73, 128, 144-145, 173, 232, 253-277, 314, 356, 358, 361-362, 368-369, 371, 385 |
| application/portfolio/stress\_test\_service.py        |       39 |        0 |    100% |           |
| application/portfolio/transaction\_service.py         |      140 |       15 |     89% |89-90, 106-107, 156, 182, 285-298 |
| application/portfolio/wrapper\_service.py             |       56 |        2 |     96% |   96, 129 |
| application/scan/\_\_init\_\_.py                      |        4 |        0 |    100% |           |
| application/scan/backfill\_service.py                 |       77 |        8 |     90% |68-71, 82-84, 151-153 |
| application/scan/backtest\_service.py                 |       80 |        2 |     98% |   45, 149 |
| application/scan/prewarm\_service.py                  |      211 |       29 |     86% |58, 82-85, 157, 169-170, 371-387, 422-423, 454-455, 486, 491-499 |
| application/scan/scan\_service.py                     |      357 |       85 |     76% |88-91, 134-137, 166-168, 193, 225, 264, 273, 283, 303, 314, 324, 334, 357, 359, 361, 416-418, 468, 527-531, 535-558, 563, 591, 599-600, 603, 644, 656-658, 673-674, 731, 745-752, 786-798, 831-836, 841-849 |
| application/services.py                               |       10 |        0 |    100% |           |
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
| domain/core/constants.py                              |      340 |        0 |    100% |           |
| domain/core/entities.py                               |      305 |        7 |     98% |36, 96, 271, 550-551, 563-564 |
| domain/core/enums.py                                  |       96 |        0 |    100% |           |
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
| infrastructure/external/notification.py               |       96 |        9 |     91% |149-150, 177, 199-205 |
| infrastructure/external/sec\_edgar.py                 |      188 |       38 |     80% |78-83, 104-105, 119, 125-129, 135-139, 212-214, 277-279, 315-316, 393-395, 419, 429-431, 439, 442, 448-449 |
| infrastructure/finmind\_adapter.py                    |        1 |        1 |      0% |         6 |
| infrastructure/jquants\_adapter.py                    |        1 |        0 |    100% |           |
| infrastructure/market\_data/\_\_init\_\_.py           |        2 |        0 |    100% |           |
| infrastructure/market\_data/crypto\_adapter.py        |      211 |      101 |     52% |84-89, 96, 102, 111-112, 123-127, 141-157, 165-166, 173-174, 185-188, 192-194, 200, 202, 211, 222-225, 235, 239, 241, 247, 251-252, 266, 270, 273, 285-293, 299-302, 306-323, 328-330, 335-372, 376-378 |
| infrastructure/market\_data/finmind\_adapter.py       |       55 |        2 |     96% |     55-56 |
| infrastructure/market\_data/jquants\_adapter.py       |       37 |        9 |     76% | 20, 26-34 |
| infrastructure/market\_data/market\_data.py           |     1385 |      536 |     61% |236, 406-407, 451-483, 549-557, 633, 644-646, 654-656, 693-701, 723-725, 731-733, 748-749, 786, 829, 944, 962, 977-979, 1021-1022, 1048-1053, 1110-1111, 1119, 1121-1123, 1152-1166, 1204-1205, 1231, 1247, 1286, 1304-1306, 1374-1407, 1427-1473, 1487-1518, 1523, 1539-1587, 1594-1597, 1610-1654, 1661-1664, 1680-1724, 1734-1752, 1815-1848, 1856-1859, 1876, 1887-1892, 1909-1946, 1955-1965, 1973-2010, 2019-2029, 2034-2041, 2060, 2079, 2093-2095, 2122, 2159-2174, 2221, 2228, 2233, 2240, 2243-2245, 2269, 2280-2282, 2284-2288, 2304-2319, 2333-2380, 2394-2426, 2437-2443, 2459-2465, 2580, 2592, 2608-2633, 2735-2761, 2786-2794, 2806, 2827, 2862, 2960, 3008-3009, 3025-3027, 3036, 3051, 3069-3071, 3080, 3095, 3117-3118, 3136-3137, 3160, 3169, 3197-3202, 3207-3210, 3230-3235, 3237-3238 |
| infrastructure/market\_data/market\_data\_resolver.py |       73 |       23 |     68% |19-25, 43-44, 47-48, 54-55, 58-59, 62, 65, 68, 71, 121, 124, 127, 132 |
| infrastructure/market\_data/toushin\_adapter.py       |       79 |        9 |     89% |41, 47, 50-51, 92, 96-97, 108, 114 |
| infrastructure/market\_data/toushin\_lib\_adapter.py  |      111 |        4 |     96% |75-77, 139 |
| infrastructure/market\_data\_resolver.py              |        1 |        1 |      0% |         6 |
| infrastructure/notification.py                        |        1 |        0 |    100% |           |
| infrastructure/persistence/\_\_init\_\_.py            |        1 |        0 |    100% |           |
| infrastructure/persistence/repositories.py            |      892 |      166 |     81% |78-86, 110-118, 144-157, 162-176, 188, 371-374, 379-383, 400, 405-406, 495, 537, 566-576, 581-584, 628, 655-665, 670-673, 712-714, 741-744, 757, 890, 1536, 1568, 1618-1621, 1626-1627, 1632-1637, 1665-1668, 1687-1690, 1725-1728, 1752, 1754, 1756, 1824-1832, 1844, 1893, 1909, 1919, 1937, 2001, 2047, 2091-2108, 2111-2115, 2120, 2135-2138, 2142, 2211, 2228-2229, 2288-2319, 2340-2345, 2362, 2368-2371, 2376-2377 |
| infrastructure/repositories.py                        |        1 |        0 |    100% |           |
| infrastructure/sec\_edgar.py                          |        1 |        0 |    100% |           |
| **TOTAL**                                             | **13153** | **1828** | **86%** |           |


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