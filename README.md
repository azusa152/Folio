# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/azusa152/Folio/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                          |    Stmts |     Miss |   Cover |   Missing |
|-------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| api/\_\_init\_\_.py                                           |        0 |        0 |    100% |           |
| api/dependencies.py                                           |       12 |        0 |    100% |           |
| api/error\_mapping.py                                         |        8 |        0 |    100% |           |
| api/rate\_limit.py                                            |        3 |        0 |    100% |           |
| api/routes/\_\_init\_\_.py                                    |        0 |        0 |    100% |           |
| api/routes/account\_routes.py                                 |       61 |        4 |     93% |50-51, 70-71 |
| api/routes/analytics\_routes.py                               |       40 |        0 |    100% |           |
| api/routes/backtest\_routes.py                                |       42 |        1 |     98% |        72 |
| api/routes/crypto\_routes.py                                  |       18 |        0 |    100% |           |
| api/routes/dividend\_routes.py                                |       30 |        2 |     93% |    70, 84 |
| api/routes/forex\_routes.py                                   |        7 |        0 |    100% |           |
| api/routes/fund\_sector\_routes.py                            |       28 |        0 |    100% |           |
| api/routes/fx\_watch\_routes.py                               |       78 |        4 |     95% |     87-92 |
| api/routes/guru\_routes.py                                    |      150 |        4 |     97% |227, 358, 606-607 |
| api/routes/holding\_routes.py                                 |       89 |        5 |     94% |180-183, 209-210 |
| api/routes/persona\_routes.py                                 |       46 |        0 |    100% |           |
| api/routes/preferences\_routes.py                             |       21 |        0 |    100% |           |
| api/routes/scan\_routes.py                                    |       83 |        6 |     93% |52-53, 61-62, 151, 187 |
| api/routes/snapshot\_routes.py                                |       81 |        9 |     89% |37-38, 41-42, 56-57, 75-76, 117 |
| api/routes/stock\_routes.py                                   |      155 |       26 |     83% |148-151, 164, 198, 262-263, 272-275, 295, 314, 323, 352-355, 367, 381-390, 402, 413, 426-428 |
| api/routes/stock\_split\_routes.py                            |       30 |        2 |     93% |    68, 82 |
| api/routes/telegram\_routes.py                                |       19 |        0 |    100% |           |
| api/routes/thesis\_routes.py                                  |       19 |        0 |    100% |           |
| api/routes/transaction\_routes.py                             |       43 |        0 |    100% |           |
| api/routes/wrapper\_routes.py                                 |      121 |        2 |     98% |  296, 349 |
| api/schemas/\_\_init\_\_.py                                   |       17 |        0 |    100% |           |
| api/schemas/account.py                                        |       27 |        0 |    100% |           |
| api/schemas/analytics.py                                      |       10 |        0 |    100% |           |
| api/schemas/backtest.py                                       |        8 |        0 |    100% |           |
| api/schemas/common.py                                         |        9 |        0 |    100% |           |
| api/schemas/crypto.py                                         |        6 |        0 |    100% |           |
| api/schemas/dividend.py                                       |       13 |        0 |    100% |           |
| api/schemas/fund\_sector.py                                   |       17 |        1 |     94% |        23 |
| api/schemas/fx\_watch.py                                      |       49 |        1 |     98% |        69 |
| api/schemas/guru.py                                           |      108 |        0 |    100% |           |
| api/schemas/guru\_analytics.py                                |       24 |        0 |    100% |           |
| api/schemas/notification.py                                   |       52 |        0 |    100% |           |
| api/schemas/portfolio.py                                      |      109 |        0 |    100% |           |
| api/schemas/scan.py                                           |       88 |        0 |    100% |           |
| api/schemas/stock.py                                          |       82 |        1 |     99% |        80 |
| api/schemas/stock\_split.py                                   |       14 |        0 |    100% |           |
| api/schemas/transaction.py                                    |       95 |        6 |     94% |64, 78, 143-145, 147 |
| api/schemas/wrapper.py                                        |       35 |        0 |    100% |           |
| application/\_\_init\_\_.py                                   |        0 |        0 |    100% |           |
| application/errors.py                                         |       13 |        1 |     92% |        28 |
| application/formatters.py                                     |      133 |        8 |     94% |154-155, 196, 343, 345, 375-377 |
| application/guru/\_\_init\_\_.py                              |        4 |        0 |    100% |           |
| application/guru/backtest\_service.py                         |      111 |       18 |     84% |62, 72, 89, 92-97, 148, 200, 212-214, 235-237, 240, 245, 260-264 |
| application/guru/guru\_service.py                             |       47 |        2 |     96% |  103, 105 |
| application/guru/heatmap\_service.py                          |       83 |       17 |     80% |40, 55-56, 62-63, 66-67, 72-77, 98, 133, 141, 149 |
| application/guru/resonance\_service.py                        |      102 |       13 |     87% |45, 87-88, 91-92, 97-102, 113-114 |
| application/messaging/\_\_init\_\_.py                         |        3 |        0 |    100% |           |
| application/messaging/notification\_service.py                |      275 |       20 |     93% |54-58, 63-68, 231, 385, 419-428, 503-504 |
| application/messaging/telegram\_settings\_service.py          |       54 |        1 |     98% |        85 |
| application/messaging/webhook\_service.py                     |      309 |       39 |     87% |81, 156-161, 224, 254, 328-337, 386, 401-402, 507-524, 532-548, 581-585, 622-626, 887-888, 913 |
| application/portfolio/\_\_init\_\_.py                         |       16 |        0 |    100% |           |
| application/portfolio/account\_service.py                     |      123 |        8 |     93% |72, 74, 144-148, 162, 225, 244, 266 |
| application/portfolio/alert\_ack\_service.py                  |       24 |        0 |    100% |           |
| application/portfolio/analytics\_service.py                   |       27 |        0 |    100% |           |
| application/portfolio/crypto\_service.py                      |       26 |        8 |     69% |15, 36, 49-53, 57 |
| application/portfolio/dividend\_service.py                    |      149 |       41 |     72% |64, 72, 80, 93-97, 122, 136-137, 161, 211-220, 229-259, 292, 320, 325, 327, 330-331, 337-338, 340 |
| application/portfolio/drift\_alert\_service.py                |       80 |       22 |     72% |54-55, 66, 69-70, 89-90, 98, 105, 128-130, 161-177, 180 |
| application/portfolio/eligibility\_service.py                 |       63 |        1 |     98% |       206 |
| application/portfolio/eligible\_sync\_service.py              |      224 |       55 |     75% |40, 68, 102, 112, 150, 152, 190, 196, 211-213, 215, 235, 252, 265-273, 284-288, 297-312, 317-324, 330-333, 341-349 |
| application/portfolio/fund\_sector\_service.py                |       21 |        0 |    100% |           |
| application/portfolio/fx\_exposure\_service.py                |      147 |       15 |     90% |112, 267, 435, 446-474, 500, 508-509 |
| application/portfolio/fx\_watch\_service.py                   |      123 |        3 |     98% |163, 230, 400 |
| application/portfolio/holding\_service.py                     |       63 |        1 |     98% |       125 |
| application/portfolio/insight\_service.py                     |       62 |        0 |    100% |           |
| application/portfolio/nav\_sync\_service.py                   |      139 |       25 |     82% |69-70, 85-87, 89, 95-96, 121-124, 147, 152-154, 211-212, 220-221, 225-229 |
| application/portfolio/pricing\_service.py                     |       51 |        1 |     98% |        53 |
| application/portfolio/rebalance\_service.py                   |      529 |       54 |     90% |158-159, 179-181, 330, 344-345, 376, 411, 416-422, 431-432, 439-453, 469-479, 572-573, 816, 911, 1018, 1032-1033, 1320-1322, 1377-1378, 1395, 1402-1403, 1429, 1433-1445, 1448 |
| application/portfolio/routing\_service.py                     |      154 |       40 |     74% |47-51, 74, 77, 88, 94-95, 100-103, 107, 121-138, 152, 168, 266, 281, 294, 305, 311 |
| application/portfolio/settlement\_service.py                  |      286 |       26 |     91% |182, 241, 334, 344, 423, 434, 445, 460, 478, 480-489, 531, 588, 596, 605, 608, 619-620, 681, 684, 728, 768-769 |
| application/portfolio/snapshot\_service.py                    |      119 |        7 |     94% |198-199, 203, 206-210, 214 |
| application/portfolio/stock\_split\_service.py                |      162 |       33 |     80% |65, 73, 128, 144-145, 173, 232, 253-284, 321, 363, 365, 368-369, 375-376, 378, 392 |
| application/portfolio/stress\_test\_service.py                |       39 |        0 |    100% |           |
| application/portfolio/transaction\_service.py                 |      138 |       15 |     89% |90-91, 107-108, 157, 183, 286-299 |
| application/portfolio/withdrawal\_service.py                  |       75 |        8 |     89% |85-88, 178, 185, 209-212 |
| application/portfolio/wrapper\_service.py                     |       65 |        1 |     98% |        46 |
| application/scan/\_\_init\_\_.py                              |        4 |        0 |    100% |           |
| application/scan/backfill\_service.py                         |       77 |        8 |     90% |68-71, 82-84, 151-153 |
| application/scan/backtest\_service.py                         |       80 |        2 |     98% |   45, 149 |
| application/scan/prewarm\_service.py                          |      223 |       34 |     85% |58, 82-85, 157, 169-170, 377-393, 428-429, 455-461, 485-486, 517, 522-530 |
| application/scan/scan\_service.py                             |      367 |       77 |     79% |101-104, 156-159, 184-186, 208, 287, 289, 291, 346, 427-429, 482, 535-538, 541-567, 574, 617, 625-626, 629, 671, 683-685, 700-701, 758, 772-779, 813-825, 858-863, 868-876 |
| application/settings/\_\_init\_\_.py                          |        2 |        0 |    100% |           |
| application/settings/persona\_service.py                      |       52 |        0 |    100% |           |
| application/settings/preferences\_service.py                  |       41 |        3 |     93% |61, 63, 67 |
| application/stock/\_\_init\_\_.py                             |        2 |        0 |    100% |           |
| application/stock/filing\_service.py                          |      194 |        9 |     95% |170-177, 217-221, 298, 302, 375 |
| application/stock/stock\_enrichment\_service.py               |      251 |       57 |     77% |82, 102-103, 109-110, 113-115, 121-124, 133-138, 150-154, 174, 269, 277-283, 300-313, 329-331, 336-338, 343-345, 369-376, 431, 501-513 |
| application/stock/stock\_service.py                           |      263 |       18 |     93% |109, 120, 209, 249, 428, 435-436, 462-466, 507-509, 565, 569, 576 |
| application/stock/stock\_thesis\_service.py                   |       26 |        0 |    100% |           |
| domain/\_\_init\_\_.py                                        |        0 |        0 |    100% |           |
| domain/analysis/\_\_init\_\_.py                               |        7 |        0 |    100% |           |
| domain/analysis/analysis.py                                   |      264 |        0 |    100% |           |
| domain/analysis/backtest.py                                   |      115 |        9 |     92% |91, 101, 122, 126, 136-137, 236, 242, 272 |
| domain/analysis/drawdown.py                                   |       60 |        0 |    100% |           |
| domain/analysis/fx\_analysis.py                               |      244 |        9 |     96% |49, 197, 237, 242, 280, 398, 491, 495-496 |
| domain/analysis/guru\_backtest.py                             |      136 |       12 |     91% |54, 75, 78, 111, 116, 130, 146, 151, 158, 171, 201, 240 |
| domain/analysis/risk\_metrics.py                              |       46 |        0 |    100% |           |
| domain/analysis/smart\_money.py                               |       27 |        1 |     96% |        35 |
| domain/constants.py                                           |        2 |        0 |    100% |           |
| domain/core/\_\_init\_\_.py                                   |        0 |        0 |    100% |           |
| domain/core/\_constants\_market.py                            |      139 |        0 |    100% |           |
| domain/core/\_constants\_nisa.py                              |        5 |        0 |    100% |           |
| domain/core/\_constants\_portfolio.py                         |       71 |        0 |    100% |           |
| domain/core/\_constants\_scan.py                              |       89 |        0 |    100% |           |
| domain/core/constants.py                                      |       38 |        0 |    100% |           |
| domain/core/entities.py                                       |      314 |        7 |     98% |37, 97, 272, 575-576, 588-589 |
| domain/core/enums.py                                          |       96 |        0 |    100% |           |
| domain/core/protocols.py                                      |        3 |        0 |    100% |           |
| domain/entities.py                                            |        1 |        0 |    100% |           |
| domain/enums.py                                               |        1 |        0 |    100% |           |
| domain/fx\_analysis.py                                        |        1 |        0 |    100% |           |
| domain/portfolio/\_\_init\_\_.py                              |       10 |        0 |    100% |           |
| domain/portfolio/allocation.py                                |       24 |        0 |    100% |           |
| domain/portfolio/asset\_location.py                           |      180 |        7 |     96% |173, 183, 246, 297, 307, 312, 333 |
| domain/portfolio/detax.py                                     |       45 |        1 |     98% |        62 |
| domain/portfolio/eligibility.py                               |       39 |        2 |     95% |   53, 104 |
| domain/portfolio/insights.py                                  |       48 |        0 |    100% |           |
| domain/portfolio/rebalance.py                                 |       43 |        0 |    100% |           |
| domain/portfolio/routing.py                                   |       34 |        3 |     91% |27, 46, 56 |
| domain/portfolio/stress\_test.py                              |       40 |        0 |    100% |           |
| domain/portfolio/tax\_wrapper.py                              |       66 |        1 |     98% |        69 |
| domain/portfolio/utils.py                                     |        2 |        0 |    100% |           |
| domain/portfolio/withdrawal.py                                |      169 |       10 |     94% |97, 111, 129, 133, 139, 143, 219, 228, 271, 404 |
| domain/protocols.py                                           |        1 |        0 |    100% |           |
| domain/rebalance.py                                           |        1 |        0 |    100% |           |
| domain/smart\_money.py                                        |        1 |        0 |    100% |           |
| domain/stress\_test.py                                        |        1 |        0 |    100% |           |
| domain/withdrawal.py                                          |        1 |        0 |    100% |           |
| infrastructure/\_\_init\_\_.py                                |        0 |        0 |    100% |           |
| infrastructure/common/\_\_init\_\_.py                         |        0 |        0 |    100% |           |
| infrastructure/common/cache.py                                |       71 |        6 |     92% |45, 47, 49, 100, 112-114 |
| infrastructure/common/config.py                               |       17 |        0 |    100% |           |
| infrastructure/common/disk\_cache.py                          |       21 |        2 |     90% |    26, 39 |
| infrastructure/common/rate\_limiter.py                        |       14 |        0 |    100% |           |
| infrastructure/crypto.py                                      |        1 |        0 |    100% |           |
| infrastructure/database.py                                    |      184 |       58 |     68% |38-47, 258-259, 298-299, 310-320, 327-328, 332-333, 354-355, 373-374, 395-396, 420-442, 455-468, 496-497 |
| infrastructure/external/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| infrastructure/external/crypto.py                             |       38 |        3 |     92% |     80-82 |
| infrastructure/external/eligible\_fund\_parser.py             |      163 |       26 |     84% |40, 43, 46-47, 64, 98-102, 122, 127-128, 139, 147, 153-154, 159, 162, 196, 215, 220, 224, 299-301 |
| infrastructure/external/notification.py                       |       96 |        9 |     91% |149-150, 177, 199-205 |
| infrastructure/external/sec\_edgar.py                         |      171 |       30 |     82% |93, 99-103, 109-113, 186-188, 251-253, 289-290, 367-369, 393, 403-405, 413, 416, 422-423 |
| infrastructure/jquants\_adapter.py                            |        1 |        0 |    100% |           |
| infrastructure/market\_data/\_\_init\_\_.py                   |        3 |        0 |    100% |           |
| infrastructure/market\_data/\_market\_data\_shared.py         |      196 |       30 |     85% |116, 270-277, 334-341, 365, 374-376, 382-384, 415, 437-439, 445-447 |
| infrastructure/market\_data/crypto\_adapter.py                |      193 |       94 |     51% |78, 82-83, 94-98, 112-128, 136-137, 144-145, 156-159, 163-165, 171, 173, 182, 193-196, 206, 210, 212, 218, 222-223, 237, 241, 244, 256-264, 270-273, 277-294, 299-301, 306-343, 347-349 |
| infrastructure/market\_data/etf.py                            |      149 |       50 |     66% |102, 117, 131-133, 153, 185-200, 224, 231, 236, 243, 246-248, 268, 279-281, 283-287, 301-316 |
| infrastructure/market\_data/finmind\_adapter.py               |       55 |        2 |     96% |     55-56 |
| infrastructure/market\_data/forex.py                          |      119 |       75 |     37% |61-92, 108, 118-134, 142, 173-175, 191-227, 235-245, 250-286, 293-303 |
| infrastructure/market\_data/formatters.py                     |       38 |        0 |    100% |           |
| infrastructure/market\_data/jquants\_adapter.py               |       37 |        9 |     76% | 20, 26-34 |
| infrastructure/market\_data/market\_data.py                   |      810 |      291 |     64% |245-246, 283, 326, 335-336, 441, 459, 474-476, 518-519, 548-550, 607-608, 616, 618-620, 649-663, 701-702, 728, 744, 783, 801-803, 871-903, 923-969, 983-1014, 1019, 1035-1083, 1090-1093, 1106-1150, 1157-1160, 1176-1221, 1231-1249, 1366-1392, 1417-1425, 1437, 1458, 1493, 1591, 1643-1644, 1660-1662, 1671, 1686, 1704-1706, 1715, 1730, 1756-1757, 1775-1776, 1799, 1808, 1836-1842, 1847-1854, 1874-1880, 1882-1883 |
| infrastructure/market\_data/market\_data\_resolver.py         |       73 |       23 |     68% |19-25, 43-44, 47-48, 54-55, 58-59, 62, 65, 68, 71, 121, 124, 127, 132 |
| infrastructure/market\_data/sentiment.py                      |      143 |       67 |     53% |92-138, 156-184, 195-201, 217-223, 329, 340, 359-384 |
| infrastructure/market\_data/toushin\_adapter.py               |       79 |        9 |     89% |41, 47, 50-51, 92, 96-97, 108, 114 |
| infrastructure/market\_data/toushin\_lib\_adapter.py          |      111 |        4 |     96% |75-77, 139 |
| infrastructure/notification.py                                |        1 |        0 |    100% |           |
| infrastructure/persistence/\_\_init\_\_.py                    |        0 |        0 |    100% |           |
| infrastructure/persistence/repositories/\_\_init\_\_.py       |       11 |        0 |    100% |           |
| infrastructure/persistence/repositories/account\_repo.py      |       21 |        0 |    100% |           |
| infrastructure/persistence/repositories/eligible\_repo.py     |      167 |       18 |     89% |47, 63, 73, 91, 155, 201, 254-262, 365, 382-383 |
| infrastructure/persistence/repositories/fund\_sector\_repo.py |       42 |        2 |     95% |    73, 93 |
| infrastructure/persistence/repositories/guru\_repo.py         |      239 |        1 |     99% |       125 |
| infrastructure/persistence/repositories/holding\_repo.py      |       63 |       14 |     78% |35, 67, 117-120, 125-126, 131-136 |
| infrastructure/persistence/repositories/nav\_repo.py          |       53 |       26 |     51% |57-88, 109-114, 131 |
| infrastructure/persistence/repositories/scan\_repo.py         |      199 |       40 |     80% |101-104, 109-113, 130, 135-136, 225, 267, 296-306, 311-314, 358, 385-395, 400-403, 442-444, 471-474, 487 |
| infrastructure/persistence/repositories/settings\_repo.py     |       30 |       12 |     60% |32-35, 54-57, 92-95 |
| infrastructure/persistence/repositories/stock\_repo.py        |       91 |       19 |     79% |44-52, 76-84, 128-142, 154 |
| infrastructure/persistence/repositories/transaction\_repo.py  |       62 |       15 |     76% |35, 37, 39, 74-77, 82-83, 126-134, 146 |
| infrastructure/repositories.py                                |        1 |        0 |    100% |           |
| infrastructure/sec\_edgar.py                                  |        1 |        0 |    100% |           |
| **TOTAL**                                                     | **13696** | **1762** | **87%** |           |


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