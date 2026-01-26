import unicodedata

def _normalizer(text: str) -> str:
   DASH_EQUIVALENTS = {
       "\u2013": "-",  # en dash
       "\u2014": "-",  # em dash
       "\u2212": "-",  # minus sign
   }
   for k, v in DASH_EQUIVALENTS.items():
       text = text.replace(k, v)
   return text

text1="- clarification - if `artifact_has_spec_gaps(artifact)`"
text2="- ideation — if `artifact_is_valid(artifact)`"

text1_ = _normalizer(text1)
text2_ = _normalizer(text2)

body1 = text1_[1:].strip()
body2 = text2_[1:].strip()

print("body1:", body1)
print("body2:", body2)

if "- if" in body1:
   print("1. yes -if")

if "- if" in body2:
   print("2. yes -if")
