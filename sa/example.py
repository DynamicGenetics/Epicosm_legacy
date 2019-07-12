import re
from collections import Counter

def tokenize(text):
    # this needs to be tested or merged with Oliver's
    for match in re.finditer(r'\w+', text, re.UNICODE):
        yield match.group(0)

import liwc
parse, category_names = liwc.load_token_parser('cleanedLIWC.dic')

input_text = '''Four score and seven years ago our fathers brought forth on
  this continent a new nation, conceived in liberty, and dedicated to the
More than 300 primary schools across England have been forced to become academies in the last three years against a backdrop of mounting opposition from parents, a Guardian investigation has revealed.

Analysis of government data has shown that 314 schools were forcibly removed from local authority control after being rated inadequate by Ofsted. The Department for Education (DfE) has paid out at least £18.4m to academy trusts for taking on the schools.

Concerns are growing, however, about the stability of the system, with evidence that a rapidly increasing number of primary schools are being passed from one trust to another after conversion, causing long-term disruption and uncertainty.

Guardian analysis of DfE data shows that the number of primary schools transferred between academy trusts following conversion has tripled in just three years, from 39 to 121. Since 2013-14 more than 300 primary academies have been rebrokered or moved between trusts  proposition that all men are created equal. Now we are engaged in a great
  civil war, testing whether that nation, or any nation so conceived and so
  dedicated, can long endure. We are met on a great battlefield of that war.
  We have come to dedicate a portion of that field, as a final resting place
  for those who here gave their lives that that nation might live. It is
  altogether fitting and proper that we should do this.'''

text_tokens = tokenize(input_text)
# now flatmap over all the categories in all of the tokens using a generator:
text_counts = Counter(category for token in text_tokens for category in parse(token))
# and print the results:
print(text_counts)
