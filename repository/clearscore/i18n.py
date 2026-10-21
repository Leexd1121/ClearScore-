"""Context-written UI copy. No online translation service is used at runtime."""
from dataclasses import dataclass, field
from string import Formatter

LANGUAGES = {"zh": "简体中文", "en": "English", "ru": "Русский", "ug": "ئۇيغۇرچە"}

# Each row is a complete UI message, not a word-for-word translation template.
ROWS = [
("window", "净谱 ClearScore · 曲谱清理", "ClearScore · Sheet music cleanup", "ClearScore · Очистка нот", "ClearScore · نوتا تازىلاش"),
("brand", "净谱", "ClearScore", "ClearScore", "ClearScore"),
("tagline", "让注意力回到音乐。", "Clearer scores. Easier practice.", "Ноты без отвлекающего фона.", "نوتىلارنى ئېنىق كۆرۈڭ."),
("local", "● 完全本地处理", "● Works offline", "● Работает офлайн", "● تورسىز ئىشلەيدۇ"),
("help", "使用说明", "How to use", "Как пользоваться", "ئىشلىتىش ئۇسۇلى"),
("import_section", "01   导入文件", "01   Open a file", "01   Открыть файл", "01   ھۆججەت ئېچىش"),
("choose", "选择一份曲谱", "Choose your sheet music", "Выберите файл с нотами", "نوتا ھۆججىتىنى تاللاڭ"),
("supported_short", "PDF · 图片 · Word DOCX", "PDF · Images · Word DOCX", "PDF · Изображения · Word DOCX", "PDF · رەسىم · Word DOCX"),
("open", "打开文件", "Open file", "Открыть файл", "ھۆججەت ئېچىش"),
("waiting", "等待导入", "No file selected", "Файл не выбран", "ھۆججەت تاللانمىدى"),
("analyze_hint", "自动分析浅灰背景", "Detects pale gray backgrounds", "Поиск светло-серого фона", "سۇس كۈلرەڭ تەگلىكنى بايقايدۇ"),
("resolution", "保留原始图片分辨率", "Keeps the original image resolution", "Исходное разрешение сохраняется", "رەسىمنىڭ ئەسلى ئېنىقلىقى ساقلىنىدۇ"),
("settings", "02   清理设置", "02   Cleanup settings", "02   Настройки очистки", "02   تازىلاش تەڭشىكى"),
("auto", "自动识别浅灰背景", "Auto-detect gray background", "Автоопределение серого фона", "كۈلرەڭ تەگلىكنى ئاپتوماتىك بايقاش"),
("staff", "保护细谱线", "Protect thin staff lines", "Защита тонких линий", "ئىنچىكە نوتا سىزىقلىرىنى قوغداش"),
("strength", "去除程度", "Removal strength", "Интенсивность очистки", "تازىلاش دەرىجىسى"),
("automatic", "自动", "Automatic", "Автоматически", "ئاپتوماتىك"),
("gentle", "轻柔", "Gentle", "Бережно", "يېنىك"),
("strong", "强力", "Stronger", "Сильнее", "كۈچلۈك"),
("strength_tip", "关闭自动后调节。强度越高，可去除的灰色越深。", "Turn off automatic detection to adjust. Higher strength removes darker gray.", "Отключите автоопределение. Чем выше интенсивность, тем более тёмный фон удаляется.", "ئاپتوماتىك بايقاشنى ئېتىپ تەڭشەڭ. دەرىجە يۇقىرى بولسا، قېنىقراق كۈلرەڭمۇ تازىلىنىدۇ."),
("limit", "适合白底曲谱中的浅灰水印。浅色符号也可能受影响，请放大核对。", "Best for pale gray watermarks on white paper. Check faint notation at a higher zoom.", "Для светло-серых водяных знаков на белом фоне. Проверьте бледные знаки при увеличении.", "ئاق تەگلىكتىكى سۇس كۈلرەڭ سۇ تامغىسىغا ماس كېلىدۇ. سۇس نوتا بەلگىلىرىنى چوڭايتىپ تەكشۈرۈڭ."),
("cancel", "取消", "Cancel", "Отмена", "ۋاز كېچىش"),
("export", "保存清理结果", "Save cleaned file", "Сохранить результат", "تازىلانغان ھۆججەتنى ساقلاش"),
("folder", "打开输出文件夹", "Show in folder", "Открыть папку с результатом", "نەتىجە قىسقۇچىنى ئېچىش"),
("footer", "本地处理 · 原件保留 · v{version}", "Offline · Original kept · v{version}", "Офлайн · Оригинал сохранён · v{version}", "تورسىز · ئەسلى نۇسخا ساقلىنىدۇ · v{version}"),
("workspace", "曲谱工作台", "Sheet music workspace", "Работа с нотами", "نوتا خىزمەت رايونى"),
("subtitle", "去掉背景干扰，留下清晰谱面。", "Remove distracting backgrounds from your scores.", "Уберите фон, который мешает читать ноты.", "نوتىلارنى ئوقۇشقا توسالغۇ بولغان تەگلىكنى تازىلاڭ."),
("cleaned", "清理后", "Cleaned", "После очистки", "تازىلانغان نۇسخا"),
("original", "原始文件", "Original", "Оригинал", "ئەسلى نۇسخا"),
("compare", "左右对比", "Side by side", "Сравнить", "سېلىشتۇرۇش"),
("changes", "改动区域", "Changed areas", "Изменённые участки", "ئۆزگەرگەن جايلار"),
("fit", "适应页面", "Fit", "Целиком", "سىغدۇرۇش"),
("width", "适应宽度", "Fit width", "По ширине", "كەڭلىككە سىغدۇرۇش"),
("drop", "把文件拖到这里", "Drop your file here", "Перетащите файл сюда", "ھۆججەتنى بۇ يەرگە سۆرەپ ئەكېلىڭ"),
("drop_sub", "或点击「打开文件」开始处理", "Or choose Open file to get started", "Или нажмите «Открыть файл»", "ياكى «ھۆججەت ئېچىش» نى بېسىڭ"),
("features", "自动检测背景   /   对比预览   /   保留原始分辨率", "Automatic detection   /   Before and after   /   Original resolution", "Автоопределение   /   Сравнение   /   Исходное разрешение", "ئاپتوماتىك بايقاش   /   سېلىشتۇرۇش   /   ئەسلى ئېنىقلىق"),
("ready", "就绪 · 支持拖放文件", "Ready · Drop a file to begin", "Готово · Перетащите файл для начала", "تەييار · باشلاش ئۈچۈن ھۆججەت ئەكېلىڭ"),
("report", "保存处理报告", "Save report", "Сохранить отчёт", "دوكلاتنى ساقلاش"),
("reading", "正在读取文件…", "Reading file…", "Чтение файла…", "ھۆججەت ئوقۇلۇۋاتىدۇ…"),
("updating", "设置已改变，正在更新预览…", "Updating preview with your settings…", "Обновляем предпросмотр…", "ئالدىن كۆرۈش يېڭىلىنىۋاتىدۇ…"),
("processing", "正在分析并清理背景…", "Analyzing and cleaning the background…", "Анализ и очистка фона…", "تەگلىك تەھلىل قىلىنىپ تازىلىنىۋاتىدۇ…"),
("page_item", "第 {n} / {count} 页", "Page {n} of {count}", "Страница {n} из {count}", "{count} بەتنىڭ {n}-بېتى"),
("image_item", "图片 {n} / {count}", "Image {n} of {count}", "Изображение {n} из {count}", "{count} رەسىمنىڭ {n}-رەسىمى"),
("frame_item", "帧 {n} / {count}", "Frame {n} of {count}", "Кадр {n} из {count}", "{count} كادىرنىڭ {n}-كادىرى"),
("unchanged_suffix", " · 原样", " · Unchanged", " · Без изменений", " · ئۆزگەرمىگەن"),
("file_meta", "{count} 项 · {size:.1f} MB", "{count} items · {size:.1f} MB", "Объектов: {count} · {size:.1f} МБ", "{count} تۈر · {size:.1f} MB"),
("processed", "已清理 {done} / {count} 项", "Cleaned {done} of {count}", "Очищено: {done} из {count}", "{count} تۈردىن {done} تۈر تازىلاندى"),
("detected", "已检测到浅灰背景", "Pale gray background detected", "Обнаружен светло-серый фон", "سۇس كۈلرەڭ تەگلىك بايقالدى"),
("not_detected", "未检测到典型浅灰背景", "No distinct pale gray background found", "Характерный серый фон не обнаружен", "ئېنىق سۇس كۈلرەڭ تەگلىك تېپىلمىدى"),
("dark_kept", "{count:,} 个深色像素保持原值", "{count:,} dark pixels left unchanged", "Тёмных пикселей без изменений: {count:,}", "{count:,} قېنىق رەڭلىك پىكسېل ئۆزگەرمىدى"),
("nothing_changed", "内容保持原样", "Content left unchanged", "Содержимое не изменено", "مەزمۇن ئۆزگەرمىدى"),
("docx_preview", "预览 Word 中的嵌入图片；导出保留文档文字和版式。", "Previewing embedded images. The Word file keeps its text and layout.", "Показаны встроенные изображения. Текст и оформление Word сохраняются.", "Word ئىچىدىكى رەسىملەر كۆرسىتىلىدۇ. تېكىست ۋە بەت ئورۇنلاشتۇرۇشى ساقلىنىدۇ."),
("navigation", "滚轮滚动 · Ctrl + 滚轮缩放 · 拖动平移", "Scroll to move · Ctrl + scroll to zoom · Drag to pan", "Колесо: прокрутка · Ctrl + колесо: масштаб · Перетаскивание: сдвиг", "چاق بىلەن سۈرۈڭ · Ctrl بىلەن چوڭايتىڭ · سۆرەپ يۆتكەڭ"),
("failed", "未完成处理", "Could not finish", "Обработка не завершена", "بىر تەرەپ قىلىش تاماملانمىدى"),
("check_file", "请检查文件后重试", "Check the file and try again", "Проверьте файл и повторите попытку", "ھۆججەتنى تەكشۈرۈپ قايتا سىناڭ"),
("source_kept", "原始文件保持不变", "The original file is unchanged", "Исходный файл не изменён", "ئەسلى ھۆججەت ئۆزگەرمىدى"),
("cancelled", "已取消处理", "Processing cancelled", "Обработка отменена", "بىر تەرەپ قىلىشتىن ۋاز كېچىلدى"),
("cancelling", "正在取消…", "Cancelling…", "Отмена…", "ۋاز كېچىلىۋاتىدۇ…"),
("difference_caption", "绿色标出预览中的改动区域", "Green highlights show changed areas", "Изменённые участки выделены зелёным", "ئۆزگەرگەن جايلار يېشىل رەڭدە كۆرسىتىلدى"),
("saved", "已保存 · {name}", "Saved · {name}", "Сохранено · {name}", "ساقلاندى · {name}"),
("report_saved", "处理报告已保存", "Report saved", "Отчёт сохранён", "دوكلات ساقلاندى"),
("error_title", "无法完成操作", "Unable to complete this action", "Не удалось выполнить действие", "مەشغۇلاتنى تاماملىغىلى بولمىدى"),
("ok", "确定", "OK", "ОК", "جەزملە"),
("all_supported", "所有支持的文件", "All supported files", "Все поддерживаемые файлы", "قوللايدىغان بارلىق ھۆججەتلەر"),
("images", "图片", "Images", "Изображения", "رەسىملەر"),
("documents", "Word 文档", "Word documents", "Документы Word", "Word پۈتۈكلىرى"),
("save", "保存", "Save", "Сохранить", "ساقلاش"),
("filename", "文件名", "File name", "Имя файла", "ھۆججەت نامى"),
("filetype", "文件类型", "File type", "Тип файла", "ھۆججەت تىپى"),
("lookin", "文件夹", "Folder", "Папка", "قىسقۇچ"),
("computer", "此电脑", "This PC", "Этот компьютер", "بۇ كومپيۇتېر"),
("lossy", "JPEG 图片（有损压缩）", "JPEG image (lossy)", "JPEG (с потерями)", "JPEG رەسىمى (سۈپىتى تۆۋەنلىشى مۇمكىن)"),
("jpeg_confirm", "JPEG 会有损压缩，并将透明区域变为白色。要保留清理后的像素和透明度，请选择 PNG 或 TIFF。仍保存为 JPEG？", "JPEG adds lossy compression and turns transparency white. Choose PNG or TIFF to keep the cleaned pixels and transparency. Save as JPEG anyway?", "JPEG сжимает изображение с потерями и заменяет прозрачность белым цветом. PNG и TIFF сохраняют пиксели и прозрачность. Всё равно сохранить в JPEG?", "JPEG پىرىسلاش سۈپەتكە تەسىر قىلىدۇ ۋە سۈزۈك جايلارنى ئاق قىلىدۇ. پىكسېل ۋە سۈزۈكلۈكنى ساقلاش ئۈچۈن PNG ياكى TIFF تاللاڭ. يەنىلا JPEG قىلىپ ساقلامسىز؟"),
("replace", "替换已有文件？", "Replace the existing file?", "Заменить существующий файл?", "مەۋجۇت ھۆججەتنى ئالماشتۇرامسىز؟"),
("back", "后退", "Back", "Назад", "كەينىگە"),
("forward", "前进", "Forward", "Вперёд", "ئالدىغا"),
("up", "上一级文件夹", "Parent folder", "На уровень выше", "ئۈستۈنكى قىسقۇچ"),
("new_folder", "新建文件夹", "New folder", "Новая папка", "يېڭى قىسقۇچ"),
("list_view", "列表", "List", "Список", "تىزىملىك"),
("detail_view", "详细信息", "Details", "Подробности", "تەپسىلات"),
("name_header", "名称", "Name", "Имя", "نامى"),
("size_header", "大小", "Size", "Размер", "ھەجىمى"),
("type_header", "类型", "Type", "Тип", "تىپى"),
("date_header", "修改时间", "Date modified", "Дата изменения", "ئۆزگەرتىلگەن ۋاقتى"),
("help_body",
"1. 打开 PDF、图片或 Word DOCX 文件。\n2. 在「左右对比」中放大检查音符、数字和细谱线。\n3. 如有残留，关闭自动并略微提高去除程度。\n4. 保存清理结果，原文件不会被覆盖。\n\n图片默认保存为无损 PNG；多帧图片可保存为多页 TIFF 或 PDF。JPEG 会再次有损压缩。\nWord 预览的是嵌入图片，并非文档页面。DOCX 导出保留文字和排版；不处理 Word 的矢量水印或浮动文字水印。旧版 .doc 请先另存为 .docx。\n\n适合白底和浅灰背景。扫描图中很浅的符号也可能被清除，请核对预览。\nCtrl+O 打开 · Ctrl+Shift+S 保存 · Ctrl+0 适应页面",
"1. Open a PDF, image, or Word DOCX file.\n2. Use Side by side and zoom in to check notes, tab numbers, and thin lines.\n3. If gray remains, turn off automatic detection and increase removal strength slightly.\n4. Save the result as a new file. Your original is never overwritten.\n\nImages default to lossless PNG. Multiple frames can be saved as a multipage TIFF or PDF. JPEG adds lossy compression.\nWord previews show embedded images, not document pages. DOCX output keeps text and layout; vector or floating-text watermarks are not removed. Save older .doc files as .docx first.\n\nBest for white paper with pale gray backgrounds. Very faint notation may also be removed: check the preview.\nCtrl+O: Open · Ctrl+Shift+S: Save · Ctrl+0: Fit",
"1. Откройте PDF, изображение или документ Word DOCX.\n2. Нажмите «Сравнить» и увеличьте изображение, чтобы проверить ноты, цифры табулатуры и тонкие линии.\n3. Если серый фон остался, отключите автоопределение и немного увеличьте интенсивность.\n4. Сохраните результат в новый файл. Оригинал не перезаписывается.\n\nПо умолчанию изображения сохраняются в PNG без потерь. Несколько кадров можно сохранить в многостраничный TIFF или PDF. JPEG использует сжатие с потерями.\nДля Word показаны встроенные изображения, а не страницы документа. DOCX сохраняет текст и оформление; векторные и плавающие текстовые водяные знаки не удаляются. Старые файлы .doc сначала сохраните как .docx.\n\nПрограмма рассчитана на светло-серый фон и белую бумагу. Очень бледные знаки тоже могут исчезнуть: проверьте предпросмотр.\nCtrl+O: открыть · Ctrl+Shift+S: сохранить · Ctrl+0: показать целиком",
"1. PDF، رەسىم ياكى Word DOCX ھۆججىتىنى ئېچىڭ.\n2. «سېلىشتۇرۇش» تا نوتا، سان ۋە ئىنچىكە سىزىقلارنى چوڭايتىپ تەكشۈرۈڭ.\n3. كۈلرەڭ قالدۇق قالسا، ئاپتوماتىك بايقاشنى ئېتىپ، تازىلاش دەرىجىسىنى سەل ئۆستۈرۈڭ.\n4. نەتىجىنى يېڭى ھۆججەتكە ساقلاڭ. ئەسلى ھۆججەت قاپلانمايدۇ.\n\nرەسىم ئادەتتە سۈپىتىنى يوقاتمايدىغان PNG شەكلىدە ساقلىنىدۇ. كۆپ كادىرلىق رەسىمنى كۆپ بەتلىك TIFF ياكى PDF قىلىپ ساقلىغىلى بولىدۇ. JPEG قايتا پىرىسلانغاندا سۈپىتى تۆۋەنلىشى مۇمكىن.\nWord ئالدىن كۆرۈشتە ھۆججەت بېتى ئەمەس، ئىچىدىكى رەسىملەر كۆرسىتىلىدۇ. DOCX تېكىست ۋە بەت ئورۇنلاشتۇرۇشىنى ساقلايدۇ. ۋېكتور ياكى لەيلىمە تېكىست سۇ تامغىسى تازىلانمايدۇ. كونا .doc ھۆججىتىنى ئاۋۋال .docx قىلىپ ساقلاڭ.\n\nئاق قەغەزدىكى سۇس كۈلرەڭ تەگلىككە ماس كېلىدۇ. بەك سۇس نوتا بەلگىلىرىمۇ تازىلىنىشى مۇمكىن، ئالدىن كۆرۈشنى تەكشۈرۈڭ.\nCtrl+O: ئېچىش · Ctrl+Shift+S: ساقلاش · Ctrl+0: سىغدۇرۇش"),
]

# Technical conditions are explained in the same language as the controls.
ERROR_ROWS = [
("missing_file", "找不到文件，请重新选择。", "The file could not be found. Select it again.", "Файл не найден. Выберите его заново.", "ھۆججەت تېپىلمىدى. قايتا تاللاڭ."),
("unsupported", "暂不支持此格式。请选择 PDF、常见图片或 DOCX。", "This format is not supported. Choose a PDF, image, or DOCX.", "Формат не поддерживается. Выберите PDF, изображение или DOCX.", "بۇ فورمات قوللانمايدۇ. PDF، رەسىم ياكى DOCX تاللاڭ."),
("legacy_word", "旧版 .doc 请先在 Word 中另存为 .docx，再导入。", "Save this older .doc file as .docx in Word, then open it here.", "Сначала сохраните старый файл .doc в формате .docx в Word.", "كونا .doc ھۆججىتىنى Word تا .docx قىلىپ ساقلاپ، قايتا ئېچىڭ."),
("file_large", "文件超过 300 MB，请先拆分。", "The file is over 300 MB. Split it into smaller files.", "Файл больше 300 МБ. Разделите его на несколько файлов.", "ھۆججەت 300 MB دىن چوڭ. ئۇنى كىچىك ھۆججەتلەرگە بۆلۈڭ."),
("image_large", "单张图片超过 6000 万像素，请先缩小。", "This image exceeds 60 megapixels. Resize it first.", "Изображение больше 60 мегапикселей. Уменьшите его размер.", "رەسىم 60 مىليون پىكسېلدىن چوڭ. ئاۋۋال كىچىكلىتىڭ."),
("too_many", "一次最多处理 300 页或帧，请拆分后导入。", "Up to 300 pages or frames can be processed at once. Split the file first.", "За один раз можно обработать до 300 страниц или кадров. Разделите файл.", "بىر قېتىمدا 300 بەت ياكى كادىرغىچە بىر تەرەپ قىلىنىدۇ. ھۆججەتنى بۆلۈڭ."),
("memory_limit", "图片总像素过多，请拆分文件。", "The combined images are too large. Split the file.", "Общий размер изображений слишком велик. Разделите файл.", "رەسىملەرنىڭ ئومۇمىي ھەجىمى بەك چوڭ. ھۆججەتنى بۆلۈڭ."),
("unsupported_color", "暂不处理 {mode} 色彩模式，以免改变颜色。", "Color mode {mode} is not processed to avoid changing colors.", "Цветовой режим {mode} не обрабатывается, чтобы не менять цвета.", "رەڭ ئۆزگىرىپ كەتمەسلىكى ئۈچۈن {mode} رەڭ ھالىتى بىر تەرەپ قىلىنمايدۇ."),
("verification_failed", "内容校验失败，已停止导出。", "The content check failed. No output was saved.", "Проверка содержимого не пройдена. Результат не сохранён.", "مەزمۇن تەكشۈرۈشىدىن ئۆتمىدى. نەتىجە ساقلانمىدى."),
("encrypted", "此 PDF 已加密，请先解锁并另存后再导入。", "This PDF is encrypted. Unlock it and save a copy first.", "PDF зашифрован. Сначала снимите защиту и сохраните копию.", "بۇ PDF شىفىرلانغان. ئاۋۋال قۇلۇپىنى ئېچىپ، كۆپەيتىپ ساقلاڭ."),
("empty_pdf", "PDF 中没有页面。", "This PDF has no pages.", "В PDF нет страниц.", "بۇ PDF دا بەت يوق."),
("forms", "此文件含表单或签名，请先另存为普通 PDF。", "This PDF contains forms or signatures. Save it as a plain PDF first.", "PDF содержит формы или подписи. Сначала сохраните его как обычный PDF.", "PDF دا جەدۋەل ياكى ئىمزا بار. ئاۋۋال ئادەتتىكى PDF قىلىپ ساقلاڭ."),
("process_failed", "无法处理此文件。请确认文件完整且未加密。", "This file could not be processed. Check that it is intact and not encrypted.", "Не удалось обработать файл. Проверьте, что он не повреждён и не зашифрован.", "ھۆججەتنى بىر تەرەپ قىلغىلى بولمىدى. ئۇنىڭ بۇزۇلمىغان ۋە شىفىرلانمىغانلىقىنى تەكشۈرۈڭ."),
("overwrite_source", "请选择新的文件名，原始曲谱不会被覆盖。", "Choose a different name. The original file cannot be overwritten.", "Выберите другое имя. Исходный файл нельзя перезаписать.", "باشقا نام تاللاڭ. ئەسلى ھۆججەتنى قاپلىغىلى بولمايدۇ."),
("missing_folder", "输出文件夹不存在。", "The output folder does not exist.", "Папка для сохранения не существует.", "ساقلايدىغان قىسقۇچ مەۋجۇت ئەمەس."),
("save_failed", "保存失败。请检查文件是否正在使用，以及文件夹权限。", "Could not save. Check folder permissions and whether the file is open elsewhere.", "Не удалось сохранить. Проверьте права на папку и не открыт ли файл в другой программе.", "ساقلىغىلى بولمىدى. قىسقۇچ ھوقۇقىنى ۋە ھۆججەتنىڭ باشقا جايدا ئېچىلغان ياكى ئېچىلمىغانلىقىنى تەكشۈرۈڭ."),
("preview_failed", "无法显示预览。", "The preview could not be displayed.", "Не удалось показать предпросмотр.", "ئالدىن كۆرۈشنى كۆرسەتكىلى بولمىدى."),
("signed_docx", "此 Word 文档带有数字签名，未作修改。", "This Word document is digitally signed and has not been changed.", "Документ Word содержит цифровую подпись и оставлен без изменений.", "بۇ Word پۈتۈكىدە رەقەملىك ئىمزا بار، ئۆزگەرتىلمىدى."),
("no_images", "此 Word 文档没有可处理的嵌入图片。文字和矢量水印保持原样。", "No supported embedded images were found. Text and vector watermarks are unchanged.", "Поддерживаемых встроенных изображений нет. Текст и векторные водяные знаки не изменены.", "بىر تەرەپ قىلغىلى بولىدىغان ئىچكى رەسىم تېپىلمىدى. تېكىست ۋە ۋېكتور سۇ تامغىسى ئۆزگەرمىدى."),
("bad_export", "此文件不支持所选的输出格式。", "The selected output format is not available for this file.", "Выбранный формат сохранения недоступен для этого файла.", "تاللانغان چىقىرىش فورماتى بۇ ھۆججەتكە ماس كەلمەيدۇ."),
("multi_export", "多页或多帧图片请保存为 TIFF 或 PDF，以保留全部内容。", "Save multiple pages or frames as TIFF or PDF to keep them all.", "Сохраните несколько страниц или кадров в TIFF или PDF, чтобы не потерять их.", "بارلىق بەت ياكى كادىرنى ساقلاش ئۈچۈن TIFF ياكى PDF تاللاڭ."),
("no_gray", "没有明显的浅灰背景。", "No distinct pale gray background.", "Нет характерного светло-серого фона.", "ئېنىق سۇس كۈلرەڭ تەگلىك يوق."),
("color_skip", "彩色或非白底内容未自动处理。", "Colorful or non-white backgrounds were left unchanged.", "Цветной или небелый фон оставлен без изменений.", "رەڭلىك ياكى ئاق بولمىغان تەگلىك ئۆزگەرتىلمىدى."),
("manual", "已按手动强度处理。", "Manual removal strength was applied.", "Применена ручная интенсивность очистки.", "قولدا تاللانغان تازىلاش دەرىجىسى قوللىنىلدى."),
("mask_skip", "带透明蒙版的 PDF 图片保持原样。", "PDF images with transparency masks were left unchanged.", "Изображения PDF с маской прозрачности не изменены.", "سۈزۈكلۈك ماسكىسى بار PDF رەسىملىرى ئۆزگەرمىدى."),
("some_unchanged", "部分内容未检测到可处理的背景，保持原样。", "Some items had no detectable background to remove and were left unchanged.", "В части объектов подходящий фон не обнаружен; они не изменены.", "بەزى تۈرلەردە تازىلىغىلى بولىدىغان تەگلىك تېپىلمىدى؛ ئۇلار ئۆزگەرمىدى."),
("unencrypted_output", "输出 PDF 不保留原文件加密。", "The output PDF will not retain encryption.", "Шифрование исходного PDF не сохраняется.", "چىقىرىلغان PDF دا ئەسلى شىفىرلاش ساقلانمايدۇ."),
("color_converted", "部分图片已转换为 RGB 以便处理。", "Some images were converted to RGB for processing.", "Часть изображений преобразована в RGB для обработки.", "بەزى رەسىملەر بىر تەرەپ قىلىش ئۈچۈن RGB غا ئۆزگەرتىلدى."),
("frames_note", "所有帧均保留；输出为静态多页文件，不保留动画播放时间。", "All frames are kept as still pages; animation timing is not exported.", "Все кадры сохранены как отдельные страницы; время анимации не сохраняется.", "بارلىق كادىرلار ئايرىم بەت قىلىپ ساقلىنىدۇ؛ كارتوننىڭ قويۇش ۋاقتى ساقلانمايدۇ."),
("analyze_progress", "正在分析 {n} / {count}", "Analyzing {n} of {count}", "Анализ: {n} из {count}", "{count} تۈرنىڭ {n} ى تەھلىل قىلىنىۋاتىدۇ"),
("clean_progress", "正在清理 {n} / {count}", "Cleaning {n} of {count}", "Очистка: {n} из {count}", "{count} تۈرنىڭ {n} ى تازىلىنىۋاتىدۇ"),
("verify_progress", "正在校验内容与尺寸", "Checking content and dimensions", "Проверка содержимого и размеров", "مەزمۇن ۋە چوڭلۇق تەكشۈرۈلۈۋاتىدۇ"),
("complete", "处理完成", "Done", "Готово", "تاماملاندى"),
]

CATALOGS = {lang: {row[0]: row[i + 1] for row in ROWS + ERROR_ROWS} for i, lang in enumerate(LANGUAGES)}


@dataclass(frozen=True)
class Message:
    key: str
    values: dict = field(default_factory=dict)

    def __str__(self):
        return tr(self.key, "zh", **self.values)


def tr(key: str | Message, language: str = "zh", **values) -> str:
    if isinstance(key, Message):
        values = {**key.values, **values}
        key = key.key
    language = language if language in LANGUAGES else "en"
    template = CATALOGS[language][key]
    if language == "ug":
        result = []
        for literal, name, spec, conversion in Formatter().parse(template):
            result.append(literal)
            if name is not None:
                value = values[name]
                formatted = format(value, spec)
                result.append(isolated(formatted) if isinstance(value, (int, float)) or name == "version" else formatted)
        # A leading Latin product/file-format name must not turn an entire
        # Uyghur paragraph into an LTR paragraph.
        return "\u200f" + "".join(result)
    return template.format(**values)


def isolated(text) -> str:
    """Keep file paths and mixed-script values in their own bidi context."""
    return "\u2068" + str(text) + "\u2069"
