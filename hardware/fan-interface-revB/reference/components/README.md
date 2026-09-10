# Component source review, 2026-09-09

These files are downloaded manufacturer/LCSC references. They are technical
evidence, not instructions for ordering or modifying the project.

| File | Source and finding |
|---|---|
| AO3400A.pdf | <https://atta.szlcsc.com/upload/public/pdf/source/20140107/1457706668533.pdf>; AOS specifies RDS(on) <=48 mΩ at VGS=2.5 V, p1-2. Selected C20917. |
| DC005.pdf | <https://atta.szlcsc.com/upload/public/pdf/source/20260728/3F4D64528080721834B5363999E43B06.pdf>; XKB DC-005-5A-2.0, 14 x 9 x 11 mm, 5 A; pin 1 center contact, pin 2 sleeve, pin 3 switched sleeve. Selected C381116. |
| DC044.pdf | <https://atta.szlcsc.com/upload/public/pdf/source/20251110/9311E98D4CAE06B23715698A58947E8C.pdf>; SHOU HAN low profile candidate rejected because drawing lists 0.5 A. |
| KH-DC044.pdf | <https://atta.szlcsc.com/upload/public/pdf/source/20210716/C2847195_E608D7B28B6781239B0777AC80FFB3DA.pdf>; mechanical drawing lacks an explicit current rating; not selected. |
| esp32-s3.pdf | <https://documentation.espressif.com/esp32-s3_datasheet_en.pdf>; v2.2, section 3 identifies GPIO3 as JTAG source strapping. TACH2 reassigned to GPIO4. |
| HXPM254.pdf | <https://datasheet.lcsc.com/datasheet/pdf/c62ff5a8cba79357cf493cd6bf152eb0.pdf?productCode=C41417323>; selected C41417323, HX PM2.54-1x11P ZC. Pin 0.64×0.4 mm; recommended hole 1.02±0.05 mm includes board's 1.00 mm; 8.50±0.15 mm housing and 3.20±0.2 mm solder tail. Drawing visually reviewed. |

Header product page: <https://www.lcsc.com/product-detail/C41417323.html>.
2026-09-09 page showed 1,180 in stock, not reserved. DFM's 22 small-pin/hole
alerts do not justify shrinking the manufacturer-recommended holes. Use
through-hole hand assembly or confirmed factory service after SMT reflow.

Molex 470531000 / C240840 has been selected from JLCEDA's real device library:
<https://item.szlcsc.com/239793.html>. Supplier library includes footprint and
3D model, with asymmetric fan locating feature. The manufacturer's sales drawing
URL below failed to download from both Mac and x570 (HTTP/2 INTERNAL_ERROR);
do not represent the original drawing as independently reviewed yet.

<https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/470/47053/470531000_sd.pdf>

Live JLCEDA catalog snapshots at selection time reported JLC stock:
C240840 5043; C381116 39004; C20917 990677. Stock is not reserved and must be
rechecked by the assembly quotation flow.
