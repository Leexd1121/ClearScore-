# Interface languages

ClearScore 1.1 supports Simplified Chinese (`zh`), English (`en`), Russian (`ru`)
and Uyghur in Arabic script (`ug`). Select a language using its own name in the
top bar. The app remembers the selection locally.

The text in `clearscore/i18n.py` is written around the action the user performs.
The app does not call a translation service. Short control labels are paired
with explanatory help and error messages, rather than copying Chinese sentence
structure into every language.

| Purpose | 中文 | English | Русский | ئۇيغۇرچە |
| --- | --- | --- | --- | --- |
| Open supported input | 打开文件 | Open file | Открыть файл | ھۆججەت ئېچىش |
| Save the processed document | 保存清理结果 | Save cleaned file | Сохранить результат | تازىلانغان ھۆججەتنى ساقلاش |
| Compare before and after | 左右对比 | Side by side | Сравнить | سېلىشتۇرۇش |
| Adjust how much gray is removed | 去除程度 | Removal strength | Интенсивность очистки | تازىلاش دەرىجىسى |
| Preserve staff rules | 保护细谱线 | Protect thin staff lines | Защита тонких линий | ئىنچىكە نوتا سىزىقلىرىنى قوغداش |

Uyghur uses a mirrored interface and a joining-capable font. Letter spacing is
disabled in Arabic-script labels. The score canvas always remains left-to-right,
so notes and tablature are never mirrored. File names and numeric substitutions
use Unicode bidirectional isolation; the strength slider increases left-to-right
in every language.

Validation covers complete message keys, matching placeholders, absence of
Chinese text in the three other message catalogs, font coverage, switching
languages after importing a file, format-specific labels, and visual review of
the four interfaces. These checks do not constitute certification by a native
language editor. Native-speaker improvements are welcome, especially for music
terminology and Uyghur usage; include the control's purpose with suggested copy.

Operating-system file names and user document text are shown as-is. English
technical field names in the optional JSON report remain stable for tools;
the report also includes warnings in the selected interface language.
