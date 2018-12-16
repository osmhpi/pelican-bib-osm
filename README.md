Pelican Bib
===========

Organize your scientific publications with BibTeX in Pelican. The package is based on Vlad's [pelican-bibtex](https://github.com/vene/pelican-bibtex). The current version is backward compatible and can replace the `pelican-bibtex` install of your current project.

Requirements
============

`pelican_bibtex` requires `pybtex`.

```bash
pip install pybtex
```

How to Use
==========

This plugin reads a user-specified BibTeX file and populates the context with
a list of publications, ready to be used in your Jinja2 template.

Configuration is simply:

```python
PUBLICATIONS_SRC = 'content/pubs.bib'
```

If the file is present and readable, you will be able to find the `publications`
variable in all templates.  It is a list of dictionaries with the following keys:

1. `key` is the BibTeX key (identifier) of the entry.
2. `year` is the year when the entry was published.  Useful for grouping by year in templates using Jinja's `groupby`
3. `text` is the HTML formatted entry, generated by `pybtex`.
4. `bibtex` is a string containing BibTeX code for the entry, useful to make it
available to people who want to cite your work.
5. `pdf`, `slides`, `poster`: in your BibTeX file, you can add these special fields,
for example:
```
@article{
   foo13
   ...
   pdf = {/papers/foo13.pdf},
   slides = {/slides/foo13.html}
}
```
This plugin will take all defined fields and make them available in the template.
If a field is not defined, the tuple field will be `None`.  Furthermore, the
fields are stripped from the generated BibTeX (found in the `bibtex` field).

Split into lists of publications
--------------------------------

You can add an extra field to each bibtex entry. This value of that field is a comma seperated list.
These values will become the keys of a list `publications_lists` containing the associated bibtex entries in your template.

For example, if you want to associate an entry with two different tags (foo-tag, bar-tag), 
you add the following field to the bib entry:

```
@article{
   foo13
   ...
   tags = {foo-tag, bar-tag}
}
```

You'll need to set `PUBLICATIONS_SPLIT_BY = 'tags'` in your `pelicanconf.py`. In your template 
(see below), you can then access these lists with the variables `publications_lists['foo-tag']` 
and `publications_lists['bar-tag']`

With `PUBLICATIONS_UNTAGGED_TITLE = 'others'` you can assign all untagged entries (i.e. entries without 
the field defined in `PUBLICATIONS_SPLIT_BY`) to the variable `publications_lists['others']`.

Template Example
================

You probably want to define a 'publications.html' direct template.  Don't forget
to add it to the 'DIRECT\_TEMPLATES' configuration key ([see here](http://docs.getpelican.com/en/stable/settings.html)). 
Note that we are escaping the BibTeX string twice in order to properly display it. 
This can be achieved using `forceescape`.

```python
{% extends "base.html" %}
{% block title %}Publications{% endblock %}
{% block content %}

<script type="text/javascript">
    function disp(s) {
        var win;
        var doc;
        win = window.open("", "WINDOWID");
        doc = win.document;
        doc.open("text/plain");
        doc.write("<pre>" + s + "</pre>");
        doc.close();
    }
</script>
<section id="content" class="body">
    <h1 class="entry-title">Publications</h1>
    <ul>
        {% for publication in publications %}
          <li id="{{ publication.key }}">{{ publication.text }}
          [&nbsp;<a href="javascript:disp('{{ publication.bibtex|replace('\n', '\\n')|escape|forceescape }}');">Bibtex</a>&nbsp;]
          {% for label, target in [('PDF', publication.pdf), ('Slides', publication.slides), ('Poster', publication.poster)] %}
            {{ "[&nbsp;<a href=\"%s\">%s</a>&nbsp;]" % (target, label) if target }}
          {% endfor %}
          </li>
        {% endfor %}
    </ul>
</section>
{% endblock %}
```


Sorting entries
---------------
The entries can be sorted by one of the attributes, for example, if you want to sort the entries by date, your unordered list would look like the following:

```python
...
    <ul>
        {% for publication in publications|sort(True, attribute='year') %}
          <li id="{{ publication.key }}">{{ publication.text }}
          [&nbsp;<a href="javascript:disp('{{ publication.bibtex|replace('\n', '\\n')|escape|forceescape }}');">Bibtex</a>&nbsp;]
          {% for label, target in [('PDF', publication.pdf), ('Slides', publication.slides), ('Poster', publication.poster)] %}
            {{ "[&nbsp;<a href=\"%s\">%s</a>&nbsp;]" % (target, label) if target }}
          {% endfor %}
          </li>
        {% endfor %}
    </ul>
...
```

The [sort builtin filter](http://jinja.pocoo.org/docs/2.10/templates/#sort) was added in version 2.6 of jinja2. 

Grouping entries
----------------

To group entries by year,

```python
    ...
    <ul>
      {% for grouper, publist in publications|groupby('year')|reverse %}
      <li> {{grouper}}
        <ul>
        {% for publication in publist %}
          <li id="{{ publication.key }}">{{ publication.text }}
          [&nbsp;<a href="javascript:disp('{{ publication.bibtex|replace('\n', '\\n')|escape|forceescape }}');">Bibtex</a>&nbsp;]
          {% for label, target in [('PDF', publication.pdf), ('Slides', publication.slides), ('Poster', publication.poster)] %}
            {{ "[&nbsp;<a href=\"%s\">%s</a>&nbsp;]" % (target, label) if target }}
          {% endfor %}
          </li>
        {% endfor %}
        </ul></li>
      {% endfor %}
    </ul>
    ...
```

Using lists of publications
---------------------------

As described above, lists of publications are stored in `publications_lists`.
You can replace `publications` from the previous example with `publications_lists['foo-tag']` to only show the publications with tagged with `foo-tag`. 

You can also iterate over the map and present all bib entries of each list. 
The section of the previous example changes to:

```python
...
<section id="content" class="body">
    <h1 class="entry-title">Publications</h1>

	{% for tag in publications_lists %}
	   {% if publications_lists|length > 1 %}
        		<h2>{{tag}}</h2>
	   {% endif %}
	   <ul>
	    {% for publication  in  publications_lists[tag] %}
                    <li id="{{ publication.bibkey }}">{{ publication.text }}
                        [&nbsp;<a href="javascript:disp('{{ publication.bibtex|replace('\n', '\\n')|escape|forceescape }}');">Bibtex</a>&nbsp;]
                        {% for label, target in [('PDF', publication.pdf), ('Slides', publication.slides), ('Poster', publication.poster)] %}
                            {{ "[&nbsp;<a href=\"%s\">%s</a>&nbsp;]" % (target, label) if target }}
                        {% endfor %}
                    </li>
	    {% endfor %}
	   </ul>
	{% endfor %}
</section>
...
```

Creating a page with a list of publications
--------------------------------------------

A common usage is displaying a list of publications of a group or an individual. If you want to have a static page displaying the publications as one of the methogs above. You need to add a template file and a page.

For example, place the template above as `publications.html` in a `content/templates` and add the follwoing to your `pelicanconf.py`:

```python
    THEME_TEMPLATES_OVERRIDES.append('templates')
```

Now, create a new page in your page folder, e.g., 'content/pages' with the content:

```python
    Publications
    ############
    
    :template: publications
```