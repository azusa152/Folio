# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                  |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------ | -------: | -------: | ------: | --------: |
| api/\_\_init\_\_.py                                   |        0 |        0 |    100% |           |
| api/dependencies.py                                   |       12 |        0 |    100% |           |
| api/rate\_limit.py                                    |        3 |        0 |    100% |           |
| api/routes/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| api/routes/account\_routes.py                         |       43 |        0 |    100% |           |
| api/routes/analytics\_routes.py                       |       40 |        0 |    100% |           |
| api/routes/backtest\_routes.py                        |       41 |        1 |     98% |        72 |
| api/routes/crypto\_routes.py                          |       18 |        0 |    100% |           |
| api/routes/forex\_routes.py                           |        6 |        0 |    100% |           |
| api/routes/fx\_watch\_routes.py                       |       77 |        4 |     95% |     85-90 |
| api/routes/guru\_routes.py                            |      149 |        4 |     97% |226, 357, 605-606 |
| api/routes/holding\_routes.py                         |       60 |        4 |     93% |100-103, 158 |
| api/routes/persona\_routes.py                         |       37 |        0 |    100% |           |
| api/routes/preferences\_routes.py                     |       16 |        0 |    100% |           |
| api/routes/scan\_routes.py                            |       82 |        6 |     93% |51-52, 60-61, 150, 186 |
| api/routes/snapshot\_routes.py                        |       80 |        9 |     89% |37-38, 41-42, 56-57, 75-76, 116 |
| api/routes/stock\_routes.py                           |      162 |       44 |     73% |135-138, 151, 157-168, 176, 190, 254-255, 264-267, 287, 303, 309, 334-339, 351-353, 367-378, 390-392, 403-405, 418-420 |
| api/routes/telegram\_routes.py                        |       19 |        0 |    100% |           |
| api/routes/thesis\_routes.py                          |       19 |        0 |    100% |           |
| api/routes/transaction\_routes.py                     |       43 |        0 |    100% |           |
| api/schemas/\_\_init\_\_.py                           |       13 |        0 |    100% |           |
| api/schemas/account.py                                |       20 |        0 |    100% |           |
| api/schemas/analytics.py                              |       10 |        0 |    100% |           |
| api/schemas/backtest.py                               |        8 |        0 |    100% |           |
| api/schemas/common.py                                 |        8 |        0 |    100% |           |
| api/schemas/crypto.py                                 |        6 |        0 |    100% |           |
| api/schemas/fx\_watch.py                              |       24 |        0 |    100% |           |
| api/schemas/guru.py                                   |      108 |        0 |    100% |           |
| api/schemas/guru\_analytics.py                        |       24 |        0 |    100% |           |
| api/schemas/notification.py                           |       41 |        0 |    100% |           |
| api/schemas/portfolio.py                              |       76 |        0 |    100% |           |
| api/schemas/scan.py                                   |       87 |        0 |    100% |           |
| api/schemas/stock.py                                  |       59 |        1 |     98% |        78 |
| api/schemas/transaction.py                            |       71 |        1 |     99% |        64 |
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
| application/messaging/webhook\_service.py             |      218 |       21 |     90% |60, 182-187, 223-228, 314-322, 387-388, 406-407, 567-569, 627-628 |
| application/portfolio/\_\_init\_\_.py                 |       10 |        0 |    100% |           |
| application/portfolio/account\_service.py             |       89 |        6 |     93% |107-111, 125, 169, 188, 210 |
| application/portfolio/analytics\_service.py           |       27 |        0 |    100% |           |
| application/portfolio/crypto\_service.py              |       26 |        8 |     69% |15, 36, 49-53, 57 |
| application/portfolio/fx\_watch\_service.py           |      117 |        3 |     97% |151, 218, 384 |
| application/portfolio/holding\_service.py             |       18 |        0 |    100% |           |
| application/portfolio/insight\_service.py             |       62 |        0 |    100% |           |
| application/portfolio/rebalance\_service.py           |      528 |       63 |     88% |137-165, 176, 279, 284-290, 298-299, 306-312, 397-398, 627, 754, 814-816, 943, 1100, 1162, 1192, 1196-1211, 1237, 1245-1246, 1325-1332, 1338-1341, 1394, 1401, 1424-1427 |
| application/portfolio/settlement\_service.py          |      217 |       33 |     85% |65, 75, 112, 153, 203, 214, 225, 240, 257-269, 297, 343-347, 353, 361, 370, 373, 384-385, 446, 449, 488, 528-529 |
| application/portfolio/snapshot\_service.py            |      120 |        7 |     94% |197-198, 202, 205-209, 213 |
| application/portfolio/stress\_test\_service.py        |       39 |        0 |    100% |           |
| application/portfolio/transaction\_service.py         |      117 |        6 |     95% |80-81, 97-98, 143, 169 |
| application/scan/\_\_init\_\_.py                      |        4 |        0 |    100% |           |
| application/scan/backfill\_service.py                 |       77 |        8 |     90% |68-71, 82-84, 151-153 |
| application/scan/backtest\_service.py                 |       80 |        2 |     98% |   45, 149 |
| application/scan/prewarm\_service.py                  |      202 |       29 |     86% |56, 80-83, 152, 164-165, 366-382, 417-418, 443-444, 475, 480-488 |
| application/scan/scan\_service.py                     |      317 |       73 |     77% |81-84, 127-130, 208, 247, 256, 266, 286, 297, 307, 317, 340, 342, 344, 399-401, 451, 511-534, 539, 567, 575-576, 579, 620, 632-634, 649-650, 696-701, 734-746, 779-784, 789-797 |
| application/services.py                               |        9 |        0 |    100% |           |
| application/settings/\_\_init\_\_.py                  |        2 |        0 |    100% |           |
| application/settings/persona\_service.py              |       53 |        0 |    100% |           |
| application/settings/preferences\_service.py          |       42 |        3 |     93% |60, 64, 93 |
| application/stock/\_\_init\_\_.py                     |        2 |        0 |    100% |           |
| application/stock/filing\_service.py                  |      193 |        9 |     95% |170-177, 217-221, 298, 302, 375 |
| application/stock/stock\_service.py                   |      396 |       61 |     85% |206, 228, 401, 408-409, 435-439, 480-482, 593, 598, 684, 704-705, 712-713, 717-719, 726-730, 740-745, 757-761, 805-818, 831-832, 837-838, 842-843, 899-906, 947-961 |
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
| domain/core/constants.py                              |      331 |        0 |    100% |           |
| domain/core/entities.py                               |      201 |        4 |     98% |280-281, 293-294 |
| domain/core/enums.py                                  |       71 |        0 |    100% |           |
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
| domain/portfolio/withdrawal.py                        |      154 |        9 |     94% |81, 95, 113, 117, 123, 127, 236, 250, 280 |
| domain/protocols.py                                   |        1 |        0 |    100% |           |
| domain/rebalance.py                                   |        1 |        0 |    100% |           |
| domain/smart\_money.py                                |        1 |        0 |    100% |           |
| domain/stress\_test.py                                |        1 |        0 |    100% |           |
| domain/withdrawal.py                                  |        1 |        0 |    100% |           |
| infrastructure/\_\_init\_\_.py                        |        0 |        0 |    100% |           |
| infrastructure/cache.py                               |       71 |        6 |     92% |44, 46, 48, 99, 111-113 |
| infrastructure/crypto.py                              |        1 |        0 |    100% |           |
| infrastructure/database.py                            |      160 |       46 |     71% |37-46, 151-152, 191-192, 203-213, 220-221, 225-226, 247-248, 266-267, 288-289, 313-335, 362-363 |
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
| infrastructure/market\_data/market\_data.py           |     1207 |      462 |     62% |226, 390-391, 433-465, 531-539, 615, 626-628, 636-638, 675-683, 705-707, 722-723, 760, 791-813, 853, 918, 936, 951-953, 995-996, 1022-1027, 1084-1085, 1090-1097, 1105, 1126-1140, 1178-1179, 1205, 1221, 1260, 1278-1280, 1348-1381, 1401-1447, 1461-1492, 1497, 1513-1557, 1567-1585, 1648-1681, 1689-1692, 1709, 1720-1725, 1742-1779, 1788-1798, 1806-1843, 1852-1862, 1867-1874, 1893, 1912, 1926-1928, 1955, 1992-2007, 2054, 2061, 2066, 2073, 2076-2078, 2102, 2113-2115, 2117-2121, 2137-2152, 2166-2213, 2227-2259, 2270-2276, 2292-2298, 2413, 2425, 2441-2466, 2568-2594, 2619-2627, 2639, 2660, 2695, 2791, 2839-2840, 2863, 2872, 2900-2905, 2910-2913, 2933-2938, 2940-2941 |
| infrastructure/market\_data/market\_data\_resolver.py |       73 |       23 |     68% |19-25, 43-44, 47-48, 54-55, 58-59, 62, 65, 68, 71, 121, 124, 127, 132 |
| infrastructure/market\_data\_resolver.py              |        1 |        1 |      0% |         6 |
| infrastructure/notification.py                        |        1 |        0 |    100% |           |
| infrastructure/persistence/\_\_init\_\_.py            |        1 |        0 |    100% |           |
| infrastructure/persistence/repositories.py            |      542 |       83 |     85% |64-72, 96-104, 130-143, 148-162, 174, 187-189, 357-360, 365-369, 386, 391-392, 481, 612, 1244, 1258, 1290, 1333-1336, 1341-1342, 1347-1352, 1357-1363, 1380-1383, 1402-1405, 1440-1443, 1467, 1469, 1471, 1506-1509, 1514-1515 |
| infrastructure/repositories.py                        |        1 |        0 |    100% |           |
| infrastructure/sec\_edgar.py                          |        1 |        0 |    100% |           |
| **TOTAL**                                             | **9685** | **1313** | **86%** |           |


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