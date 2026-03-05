#### 4) Build a calibration set using interior sampling
Construct a fixed calibration set that stresses boundary decisions.
- Order all responses for this dimension by length (shortest → longest).
- Discard the single shortest and single longest responses.
- From the remaining set, sample uniformly across interior quantiles.
- Target 25–40 cells total.
- If fewer than 30 valid cells exist, include all.
Purpose:
- Concentrate on ambiguous, mid-spectrum responses.
- Avoid trivial failures and obvious exemplars.
- Ensure even coverage of the decision surface.
Deliverable: a fixed list of cell or row IDs.  
`CAL_PPP_SectionA_Step04_calibration_set_v01`


CAL_PPP_SectionA_Step04_calibration_set_v01.csv


for the script below, I am still seeing zero flags.  Investigate the cause that one (or more) of the SectionXResponse__wc columns is being imported as text rather than number in cleaned_entries. In that case, the sampler filters everything out as “not numeric”, yielding empty SampleA lists. The fix is to add a Table.TransformColumnTypes for the five __wc columns up front.  Add in this fix