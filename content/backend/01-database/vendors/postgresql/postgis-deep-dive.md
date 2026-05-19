---
title: "PostGIS Deep Dive：Geometry / Geography 型別、GiST 空間索引跟 ST_* 函式生態"
date: 2026-05-19
description: "PostGIS 是 PG extension、加 *geometry* / *geography* 型別、GiST 空間索引跟 1000+ ST_* 函式、把 PG 變成功能完整 GIS DB（跟 Oracle Spatial / SQL Server geography 並列）。本文走 geometry vs geography 取捨、SRID 跟投影系統、GiST 空間索引機制、5 production 踩雷（geometry 用錯 SRID / geography 不能用所有 ST_ 函式 / GiST index 不對 ST_DWithin 生效 / cluster on geom 後 BRIN 失效 / EWKB vs WKB 跨工具相容）、GIS workload 的 PG vs 專業 GIS DB 對比"
weight: 31
tags: ["backend", "database", "postgresql", "postgis", "gis", "spatial", "extension", "deep-article"]
---

> 本文是 [PostgreSQL](/backend/01-database/vendors/postgresql/) overview 的 implementation-layer deep article。Overview 已說明 PG 在 OLTP 譜系的定位、本文聚焦 *PostGIS extension* — PG 變 GIS DB 的標配、跟 [extension-ecosystem](/backend/01-database/vendors/postgresql/extension-ecosystem/) 是 *單一 extension 細節 vs ecosystem 全景* 的關係。

---

## PostGIS 是 PG 的 *GIS Specialization*

PostGIS 是 PG 最成熟的 extension 之一（2001 年起、25 年歷史）、產業地位等同 OracleSpatial / SQL Server geography：

```sql
CREATE EXTENSION postgis;
```

加完後 PG 多兩件事：

1. **空間型別**：`geometry`（平面）/ `geography`（地球曲面）/ `raster`（柵格）
2. **1000+ 函式**：`ST_Distance` / `ST_Within` / `ST_Buffer` / `ST_Intersects` 等

用 PostGIS 解的典型 workload：

- 「離我最近的 N 家店」（k-NN）
- 「半徑 1km 內的所有 POI」（radius query）
- 「兩個 polygon 是否重疊」（intersection）
- 「polyline 總長度」（measurement）
- 「行政區包含哪些 point」（containment）

## Geometry vs Geography：選錯付學費

PostGIS 提供兩種空間型別、用途完全不同：

| 維度        | `geometry`                     | `geography`          |
| ----------- | ------------------------------ | -------------------- |
| 座標系統    | 平面（笛卡兒）                 | 地球曲面（spheroid） |
| 距離單位    | 座標系統決定（meter / degree） | 永遠 meter           |
| 跨經度 180° | 不處理                         | 自動處理             |
| 適用範圍    | 小區域（單一城市 / 國家）      | 全球                 |
| 函式覆蓋    | 1000+ 函式                     | 約 300 函式          |
| 效能        | 快（平面計算）                 | 慢 2-5x（球面計算）  |
| Index 行為  | GiST 直接                      | GiST 直接            |

**選 `geography` 的場景**：

- 全球範圍 application（跨國 / 跨大陸）
- 距離精準度要求高（球面比平面誤差小）
- 不需要複雜空間運算（geography 函式較少）

**選 `geometry` 的場景**：

- 單一城市 / 國家內 application
- 需要完整 ST_* 函式（90% 函式只支援 geometry）
- 效能敏感

實務多數 production 選 `geometry` + 適合的 SRID（用 local projection）— 既快又精準。

## SRID 跟 Projection：為什麼 4326 vs 3857 是 GIS 第一課

SRID（Spatial Reference System Identifier）定義「座標數字怎麼解讀」：

| SRID | 名稱                 | 適用                            |
| ---- | -------------------- | ------------------------------- |
| 4326 | WGS 84（GPS）        | 經緯度、最常見、Google Maps API |
| 3857 | Web Mercator         | Web tile map（OpenStreetMap）   |
| 3826 | TWD97 / TM2 zone 121 | 台灣 local projection、米為單位 |
| 2272 | NAD83 / Pennsylvania | 美國 state plane（各州不同）    |

**為什麼選 local projection（3826）而不是經緯度（4326）**：

- 經緯度單位是 *度*、不是距離 — `ST_Distance` 直接算出來是「度」、不是「米」
- 距離計算需 `ST_DistanceSphere` 或 `geography` cast、計算 cost 高
- Local projection 是「平面投影」、`ST_Distance` 直接是米、`ST_Area` 直接是平方米

```sql
-- 4326 經緯度直接算 → 結果不是米
SELECT ST_Distance(
    ST_SetSRID(ST_MakePoint(121.5654, 25.0330), 4326),  -- 台北 101
    ST_SetSRID(ST_MakePoint(121.5170, 25.0478), 4326)   -- 台北車站
);  -- ~0.05（這是「度」）

-- 轉 3826（台灣本地投影）才是米
SELECT ST_Distance(
    ST_Transform(ST_SetSRID(ST_MakePoint(121.5654, 25.0330), 4326), 3826),
    ST_Transform(ST_SetSRID(ST_MakePoint(121.5170, 25.0478), 4326), 3826)
);  -- ~5300（米）

-- 或用 geography cast
SELECT ST_Distance(
    ST_SetSRID(ST_MakePoint(121.5654, 25.0330), 4326)::geography,
    ST_SetSRID(ST_MakePoint(121.5170, 25.0478), 4326)::geography
);  -- ~5300（米）
```

**典型 schema 設計**（台灣 application）：

```sql
CREATE TABLE pois (
    id SERIAL PRIMARY KEY,
    name TEXT,
    -- 儲存 4326（跟 Google Maps API 對齊）
    location_4326 geometry(Point, 4326),
    -- 預計算 3826（給距離 / 面積 query 用）
    location_3826 geometry(Point, 3826) GENERATED ALWAYS AS
        (ST_Transform(location_4326, 3826)) STORED
);

CREATE INDEX idx_pois_location_3826 ON pois USING GIST (location_3826);
```

## GiST 空間索引：R-tree 的 PG 實作

PostGIS 用 PG 內建 GiST 做空間索引（內部是 R-tree 變體）：

```sql
CREATE INDEX idx_pois_geom ON pois USING GIST (location_3826);
```

GiST 對空間 query 加速的場景：

```sql
-- 範圍 query（box overlap）
SELECT * FROM pois
WHERE location_3826 && ST_MakeEnvelope(290000, 2760000, 305000, 2775000, 3826);

-- 半徑 query（用 ST_DWithin 才走 index）
SELECT * FROM pois
WHERE ST_DWithin(location_3826, ST_SetSRID(ST_MakePoint(300000, 2770000), 3826), 1000);

-- k-NN（PostGIS 2.0+ <-> operator）
SELECT id, name, location_3826 <-> ST_SetSRID(ST_MakePoint(300000, 2770000), 3826) AS dist
FROM pois
ORDER BY location_3826 <-> ST_SetSRID(ST_MakePoint(300000, 2770000), 3826)
LIMIT 10;
```

**index 用沒用到的關鍵**：

| Query 寫法                     | 走 index？         |
| ------------------------------ | ------------------ |
| `ST_DWithin(a, b, dist)`       | 是                 |
| `ST_Distance(a, b) < dist`     | 否（必 full scan） |
| `a && bbox`                    | 是                 |
| `ST_Intersects(a, bbox)`       | 是                 |
| `a <-> b ORDER BY ... LIMIT n` | 是（k-NN）         |
| `ST_Equals(a, b)`              | 否                 |

Production 寫法守則：能用 `ST_DWithin` 就不用 `ST_Distance(...) < ?`、語意一樣但 index 行為差很多。

## ST_* 函式生態：產業級全套

PostGIS 1000+ 函式分類（典型用到的）：

| 類別        | 代表函式                                                         |
| ----------- | ---------------------------------------------------------------- |
| 建構        | `ST_MakePoint` / `ST_MakeLine` / `ST_MakePolygon`                |
| 關係判定    | `ST_Intersects` / `ST_Within` / `ST_Contains` / `ST_Touches`     |
| 距離 / 大小 | `ST_Distance` / `ST_DWithin` / `ST_Length` / `ST_Area`           |
| 變換        | `ST_Buffer` / `ST_Union` / `ST_Difference` / `ST_Intersection`   |
| 投影        | `ST_Transform` / `ST_SetSRID`                                    |
| 格式轉換    | `ST_AsGeoJSON` / `ST_AsKML` / `ST_AsText` / `ST_GeomFromGeoJSON` |
| 路徑 / 拓樸 | `ST_ShortestLine` / `ST_LineMerge`                               |
| 聚合        | `ST_Collect` / `ST_ConvexHull` / `ST_Centroid`                   |
| 簡化        | `ST_Simplify` / `ST_SimplifyPreserveTopology`                    |

**Web tile 場景**典型 query：

```sql
-- 給定 z/x/y tile、找這個 tile 內的所有 POI
SELECT id, name, ST_AsMVTGeom(location_3857, ST_TileEnvelope(z, x, y)) AS geom
FROM pois
WHERE location_3857 && ST_TileEnvelope(z, x, y);
```

`ST_AsMVTGeom` + `ST_AsMVT` 直接產 Mapbox Vector Tile binary、給前端 Leaflet / Mapbox GL JS 用。

## 5 個 Production 踩雷

### Case 1：Geometry 用錯 SRID

**情境**：app 寫入時用 4326、query 時用 3826 ST_Transform、忘記給某個 column 設 SRID、index 失效。

修法：

```sql
-- 確認 SRID
SELECT ST_SRID(location) FROM pois LIMIT 1;

-- 強 type 約束（column type 寫死 SRID）
ALTER TABLE pois ALTER COLUMN location TYPE geometry(Point, 4326)
USING ST_SetSRID(location, 4326);

-- Check constraint 防錯
ALTER TABLE pois ADD CONSTRAINT chk_location_srid
CHECK (ST_SRID(location) = 4326);
```

### Case 2：Geography 不能用所有 ST_* 函式

**情境**：用 `geography` 想跑 `ST_Buffer`、報錯或結果不對。

`ST_Buffer` 對 geography 走 spheroid 近似、邊界 case 結果跟 geometry 不一致；很多函式（`ST_Voronoi` / `ST_Delaunay` 等）只支援 geometry。

修法：

- 簡單距離 query 用 geography
- 複雜空間運算用 geometry + 適合 projection
- 不確定哪些函式支援 geography、看 PostGIS docs *Geography Support Functions* 清單

### Case 3：GiST index 不對 ST_Distance 生效

**情境**：query `ST_Distance(location, ?) < 1000`、`EXPLAIN` 顯示 full scan、加 index 也沒用。

`ST_Distance` 算完才 filter、planner 沒辦法用 GiST。

修法：

- 改 `ST_DWithin(location, ?, 1000)` — 語意一樣、會走 GiST
- 確認 index 是對 *被 query 的 column* 建的（不是 transform 後的 expression）

### Case 4：CLUSTER on geom 後 BRIN 失效

**情境**：對 `pois` 跑 `CLUSTER pois USING idx_pois_geom` 想加速空間查、但同時對 `created_at` 用 BRIN index、BRIN 完全失效。

CLUSTER 重組 physical order 跟 GiST 對齊、`created_at` physical order correlation 從 1.0 變 0.0、BRIN range 沒選擇性。

修法：

- 不要 CLUSTER 大表（一次性、影響其他 column）
- 換 partition by time + GiST per-partition（取兩者）
- 看 [index-selection](/backend/01-database/vendors/postgresql/index-selection/) 的 BRIN 段

### Case 5：EWKB vs WKB 跨工具相容

**情境**：用 PostGIS export 給其他 GIS 工具（QGIS / Shapely / ogr2ogr）、resort 抱怨格式不對。

PostGIS 內部用 EWKB（Extended Well-Known Binary）— 多帶 SRID。多數 GIS 工具讀 WKB（標準）。

修法：

```sql
-- Export 標準 WKB
SELECT ST_AsBinary(geom) FROM pois;

-- 或 GeoJSON（跨工具最相容）
SELECT ST_AsGeoJSON(geom) FROM pois;

-- 或 Shapefile via ogr2ogr
-- ogr2ogr -f "ESRI Shapefile" output.shp PG:"..." -sql "SELECT * FROM pois"
```

## 跟專業 GIS DB 對比

| 維度            | PostGIS                      | Oracle Spatial | SQL Server geography | MongoDB GeoJSON   |
| --------------- | ---------------------------- | -------------- | -------------------- | ----------------- |
| 函式覆蓋        | 1000+                        | 800+           | 200+                 | ~20               |
| Raster 支援     | 是                           | 是             | 否                   | 否                |
| Topology        | 是（PostGIS Topology）       | 是             | 否                   | 否                |
| 3D 支援         | 是（PostGIS SFCGAL）         | 是             | 部分                 | 否                |
| License         | GPL                          | 商業           | 商業                 | 開源              |
| Tile generation | 內建（ST_AsMVT）             | 否             | 否                   | 否                |
| 跟 PG 整合      | 完美                         | 跟 Oracle 一體 | 跟 SQL Server 一體   | 獨立              |
| 工業界使用      | OpenStreetMap / 各國國土測繪 | 大型企業       | Microsoft 生態       | 簡單 location app |

**選 PostGIS 的場景**（90% GIS workload）：

- Application 已用 PG
- 需要完整 GIS 函式生態（路網 / 等高線 / 流域分析）
- 開源 / cost 敏感
- 跟 OGR / GDAL / QGIS 互通

**選專業 GIS DB 的場景**：

- 已綁定 Oracle / SQL Server license
- 極專業 GIS（3D 城市模型 / LIDAR / GPU 加速）
- 純 location app 不需 relational（MongoDB GeoJSON 足夠）

## 相關連結

- [extension-ecosystem](/backend/01-database/vendors/postgresql/extension-ecosystem/)：其他 PG extension
- [index-selection](/backend/01-database/vendors/postgresql/index-selection/)：GiST 跟其他 index 對比
- [query-optimization](/backend/01-database/vendors/postgresql/query-optimization/)：空間 query 的 EXPLAIN
- [jsonb-deep-dive](/backend/01-database/vendors/postgresql/jsonb-deep-dive/)：POI metadata 用 JSONB 儲存

## 下一步

- 看 [extension-ecosystem](/backend/01-database/vendors/postgresql/extension-ecosystem/) 探索其他 PG 擴展可能
- 回 [PostgreSQL overview](/backend/01-database/vendors/postgresql/) 看全圖
