from typing import Literal

EncodingErrorPolicy = Literal['strict', 'ignore', 'replace', 'backslashreplace', 'surrogateescape']
TextEncodingErrorPolicy = Literal[EncodingErrorPolicy, 'xmlcharrefreplace', 'namereplace']
