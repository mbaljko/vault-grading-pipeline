ok, we need to revise this design note.

first, when I do a raw database export in moodle. I get a csv that I bring into an excel workbook.  

Then I bring in an copy of the gradesheet that is needed to do the grade upload.  Only students in valid enrolment standing can have grades uploaded. 

  

Then I have MCode scripts that perform validation.  For instance, not every student submission needs to be graded because they are no longer in the course.  So "__join_status" tells us this.  

  

The section 3 language is abstract and not aligned with the concrete instantiations that I use.  It is fine to keep the abstract language for the design document, but I need a subsection that says the concrete instantiation.