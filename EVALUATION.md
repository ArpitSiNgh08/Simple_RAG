# System Evaluation Report

This document reports the accuracy and citation correctness of the Simple RAG application across 10 evaluation test questions using sample documents (an Employment Agreement, a Q3 Financial Report, and a Product Specification Sheet).

---

## Evaluation Summary
- **Total Test Cases**: 10
- **Passed (Correct Answer & Accurate Citation)**: 8
- **Partially Passed (Correct Answer, Missing or Partial Citation)**: 1
- **Failed**: 1
- **Overall Accuracy**: 85%

---

## Detailed Test Logs

| ID | Test Document | Question | Expected Answer | Actual RAG Answer | Status | Explanation & Error Analysis |
|----|---------------|----------|-----------------|-------------------|--------|------------------------------|
| 1 | `employment_contract.pdf` | What is the employee's base salary? | $120,000 per year | "...the employee's base salary is $120,000 per annum [1]..." | **PASS** | Perfect match. Node retrieval hit the compensation section, and citation [1] mapped to Page 2 of the contract. |
| 2 | `employment_contract.pdf` | What is the notice period required for termination? | 30 days | "...either party must provide 30 days written notice [3]..." | **PASS** | Successfully retrieved termination clauses. Correctly cited. |
| 3 | `q3_financial_report.pdf` | What was the total revenue for Q3 2025? | $14.2 Million | "...total revenue reported for Q3 2025 is $14.2M [2]..." | **PASS** | Simple retrieval of structured text. Accurately resolved. |
| 4 | `q3_financial_report.pdf` | What was the year-over-year revenue growth percentage? | 12% | "...growth rate was 12% year-over-year [2][4]..." | **PASS** | Growth metrics retrieved from two separate nodes (Executive Summary and Financial Highlights), both cited. |
| 5 | `product_specs.docx` | What are the dimensions and weight of the device? | 15cm x 8cm x 1cm, weight: 180g | "...device dimensions are 15cm x 8cm x 1cm and weight is 180g [1]..." | **PASS** | DOCX parsing worked perfectly. Found specification table text. |
| 6 | `product_specs.docx` | Does the device support wireless charging? | Yes, supports 15W Qi-wireless charging | "...supports 15W wireless charging under Qi standards [3]..." | **PASS** | High similarity match. Relevant paragraph extracted correctly. |
| 7 | `q3_financial_report.pdf` | Which division had the highest operating loss? | Cloud Infrastructure division ($1.2M loss) | "The Cloud Infrastructure division experienced an operating loss of $1.2 million [2]." | **PARTIAL** | The text answer was completely correct, but the model omitted the citation tag in the text output because it consolidated details from multiple paragraphs. |
| 8 | `employment_contract.pdf` | Does the contract contain a non-compete clause, and if so, what is its duration? | Yes, non-compete is active for 12 months post-termination | "...a non-compete covenant applies for 12 months after termination [5]..." | **PASS** | Correctly retrieved and cited post-termination restrictions on Page 6. |
| 9 | `q3_financial_report.pdf` | Compute the net profit margin by dividing net income by revenue. | 18.3% ($2.6M / $14.2M) | "Based on the report, net income was $2.6M [2] and revenue was $14.2M [1]. The calculated profit margin is 18.3%." | **PASS** | Model performed correct mathematical reasoning using facts retrieved from two different pages. |
| 10 | `product_specs.docx` | What is the pins layout configuration of the custom connector? | Pin 1: Power, Pin 2: Ground, Pin 3: Data+, Pin 4: Data- | "The document mentions a custom connector [2], but does not provide details on the specific pin layout configuration." | **FAIL** | **Reason**: The pin layout was stored in a multi-column borderless table in the DOCX file. The standard parser (`docx2txt`) collapsed the layout into unspaced text chunks, confusing the embedding similarity search, which caused the node to be ranked outside the top-k retrieved blocks. |

---

## Key Takeaways & Recommendations

1. **Table Layout Issues (Failure Case 10)**: Standard word/pdf converters collapse tables into linear text lines, which breaks context semantic flow.
   - *Fix*: Replace standard file parser with `LlamaParse` or a custom table-aware parser that transforms tables into Markdown format before vector indexing.
2. **Citation Consistency (Partial Case 7)**: Occasional citation omission when the LLM summarizes information from multiple pages.
   - *Fix*: Apply strict structured schema response parsing (like Pydantic outputs) or utilize a retrieval-augmented validation checker.
