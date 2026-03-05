```

Yeah, with Html.Table() + per-cell transforms across 5 response columns, 2+ minutes is completely plausible. Power Query is basically doing a small HTML parse hundreds of times, then you unpivot (multiplying rows), then you compute word counts. That combination is expensive.

  

Here’s what is most likely making it slow, and what to change (in the order that usually gives the biggest win).

  

### **1)** 

### **Html.Table()**

###  **is the main cost centre**

  

In your StripHtmlSafe, you do:

- build wrapped = "<div>...</div>"
    
- run Html.Table(wrapped, {{"t", "//text()"}}) inside a try
    
- fall back only on error
    

  

That means you’re parsing HTML for almost every non-null response, even if the text has no tags.

  

Fix: only call Html.Table() when you actually see < / > patterns that look like tags.

  

Rule of thumb gate:

- if the text does **not** contain < then skip parsing
    
- if it only contains `<br then handle with the br replacement and skip parsing
    
- otherwise parse
    

  

### **2) You’re doing the cleaning before unpivot, across multiple columns**

  

You currently Table.TransformColumns(Source, {{"SectionAResponse", StripHtmlSafe}, ...}) in wide form. That means PQ is applying expensive functions across 5 big columns on the wide table.

  

Better approach for performance:

- unpivot first (cheap)
    
- clean **one** response_text column (one transform instead of five)
    
- then word count on that one column
    

  

This also makes your “dynamic response fields” requirement (everything before Tags) much easier.

  

### **3) You’re adding** 

### **__row_id**

### **before**

###  **unpivot and then prefixing each of 5 columns row-by-row**

  

Table.TransformRows + Record.TransformFields across multiple columns is also expensive.

  

If you unpivot first, you can add the +++submission_id=... wrapper once per long-row (one field), not five per wide-row.

  

### **4) Word count is costly and you’re doing it for every long-row**

  

Word count after unpivot means you do it eligible_submissions × components. That’s fine if you need it, but it’s extra cost.

  

Two options:

- keep it, but do it last (after filtering)
    
- or make it optional / separate query
    

  

### **5) Power Query may be recomputing steps repeatedly (lack of buffering)**

  

When PQ references the same upstream table multiple times, or when you do joins + expansions, PQ sometimes re-evaluates earlier steps.

  

Strategic Table.Buffer() can help, but only in the right place (too much buffering can make it worse).

  

A good place:

- after filtering validation to matched_unique
    
- after the join result if it gets reused
    

  

### **Concrete path to get this under ~20–40 seconds**

  

If you’re OK with changing the structure (you already want to unpivot dynamically), the best performance move is:

1. Identify response columns dynamically (all columns before Tags)
    
2. Unpivot those into component_id / response_text
    
3. Join to validation once
    
4. Clean response_text with a gated HTML stripper
    
5. Prefix +++submission_id=... once
    
6. Word count last, or move to a separate query
    

  

If you want, I can rewrite 02_cleaning.pq to implement that structure and the HTML gate, and it will be dramatically faster.

  

### **Quick sanity check: why 2 minutes** 

### **right now**

  

Given your manifest numbers:

- 401 eligible submissions
    
- 5 components
    
- long rows = 2005
    
- expensive HTML parse potentially on most of the 2005 cells
    

  

Even if Html.Table() averaged 40–60 ms per call (often worse), that alone can hit 80–120 seconds.

  

### **Two immediate “triage” toggles if you need speed today**

- Temporarily bypass Html.Table() completely and use only StripTagsFallback + <br> replacements.
    
- Temporarily disable response_wc calculation.
    

  

Both should cut runtime sharply, even without restructuring.

  

If you want me to proceed: do you need true HTML-to-text extraction (preserving text nodes) or is “strip tags + handle <br>” good enough for these LMS exports?

```