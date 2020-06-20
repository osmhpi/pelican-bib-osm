# -*- coding: utf-8 -*-

"""
Pelican Bib
===========

A Pelican plugin that populates the context with a list of formatted
citations, loaded from a BibTeX file at a configurable path.

The use case for now is to generate a "Publications" page for academic
websites.

Configuration
-------------

``generator.settings['PUBLICATIONS_SRC']``:
    Local path to the BibTeX file to read.
    Each generator contains this list of publications.

``generator.settings['PUBLICATIONS_SPLIT_BY']``:
    The name of the bibtex field used for splitting the publications.
    No splitting if title is not provided.

``generator.settings['PUBLICATIONS_UNTAGGED_TITLE']``:
    The title of the header for all untagged entries.
    No such list if title is not provided.

``generator.settings['PUBLICATIONS_DECORATE_HTML']``:
    If set to True, elements of a publication entry (e.g. names, title)
    will be decorated with a <span> tag with a specific class name

``generator.settings['PUBLICATIONS_DEFAULT_TEMPLATE']``:
    The name of the template used as default if there is no
    template name argument present in the ``bibliography`` directive.
    ``bibliography`` if no value provided.

"""
# Author: Vlad Niculae <vlad@vene.ro>
# Unlicense (see UNLICENSE for details)

import logging
logger = logging.getLogger(__name__)

from ast import literal_eval
from os import sep as path_separator
from os.path import join, basename, dirname, abspath
from re import sub as replace

from docutils import nodes, utils
from docutils.parsers.rst import directives, Directive
from jinja2 import Template
from pelican import signals

from .htmldecorator import get_style_type


def generator_init(generator):
    """ Populates context with a list of BibTeX publications.

    ``generator.settings['PUBLICATIONS_SRC']``:
        Local path to the BibTeX file to read.

    Output
    ------

    ``generator.context['publications_lists']``:
        A map with keys retrieved from the field named in PUBLICATIONS_SPLIT_TAG.
        Values are lists of tuples (key, year, text, bibtex, pdf, slides, poster)
        See Readme.md for more details.

    ``generator.context['publications']``:
        Contains all publications as a list of tuples
        (key, year, text, bibtex, pdf, slides, poster).
        See Readme.md for more details.
    """
    if 'PUBLICATIONS_SRC'in generator.settings:
        refs_files = generator.settings['PUBLICATIONS_SRC']
        if isinstance(refs_files, str):
            refs_files = [ refs_files ]
        add_publications_to_context(generator, refs_files)


def add_publications_to_context(generator, refs_files, refs_string=None, pybtex_style_args={}):
    """ Populates context with a list of BibTeX publications. """
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO
    try:
        from pybtex.database.input.bibtex import Parser
        from pybtex.database.output.bibtex import Writer
        from pybtex.database import BibliographyData, PybtexError
        from pybtex.backends import html
        from pybtex.style.formatting import BaseStyle, plain
    except ImportError:
        logger.warn('`pelican_bib` failed to load dependency `pybtex`')
        return

    decorate_html = generator.settings.get('PUBLICATIONS_DECORATE_HTML', False)

    plugin_path = generator.settings.get('PUBLICATIONS_PLUGIN_PATH', 'plugins')
    import sys
    sys.path.append(plugin_path)

    kwargs = generator.settings.get('PUBLICATIONS_STYLE_ARGS', {})
    kwargs.update(pybtex_style_args)
    style_type = get_style_type(plain.Style, decorate_html)
    style = style_type(**kwargs)

    if generator.settings.get('PUBLICATIONS_CUSTOM_STYLE', False):
        try:
            from pybtex_plugins import PelicanStyle
            if not isinstance(PelicanStyle, type) or not issubclass(PelicanStyle, BaseStyle):
                raise TypeError()
            style_type = get_style_type(PelicanStyle, decorate_html)
            style = style_type(**kwargs)
        except ImportError as e:
            logger.warn(str(e))
            logger.warn('pybtex_plugins.PelicanStyle not found, using Pybtex plain style')
        except TypeError:
            logger.warn('PelicanStyle must be a subclass of pybtex.style.formatting.BaseStyle')

    # collect entries
    bibdata_entries = {}
    for file in refs_files:
        bibdata_entries.update(Parser().parse_file(file).entries)
    if refs_string:
        bibdata_entries.update(Parser().parse_string(refs_string).entries)

    publications = []
    publications_lists = {}
    publications_untagged = []

    split_by = generator.settings.get('PUBLICATIONS_SPLIT_BY', None)
    untagged_title = generator.settings.get('PUBLICATIONS_UNTAGGED_TITLE', None)

    # format entries
    html_backend = html.Backend()
    formatted_entries = style.format_entries(bibdata_entries.values())

    for formatted_entry in formatted_entries:
        key = formatted_entry.key
        entry = bibdata_entries[key]
        year = entry.fields.get('year')
        # This shouldn't really stay in the field dict
        # but new versions of pybtex don't support pop
        pdf = entry.fields.get('pdf', None)
        slides = entry.fields.get('slides', None)
        poster = entry.fields.get('poster', None)

        tags = []
        if split_by:
            tags = entry.fields.get(split_by, [])

            # parse to list, and trim each string
            if tags:

                tags = [tag.strip() for tag in tags.split(',')]

                # create keys in publications_lists if at least one
                # tag is given
                for tag in tags:
                    publications_lists[tag] = publications_lists.get(tag, [])


        #render the bibtex string for the entry
        bib_buf = StringIO()
        bibdata_this = BibliographyData(entries={key: entry})
        Writer().write_stream(bibdata_this, bib_buf)

        # convert decorated html tags
        # `<:bib-xyz>abc</:bib-xyz>` => `<span class="bib-xyz">abc</span>`
        text = formatted_entry.text.render(html_backend)
        text = replace(r'<:([^>]*)>', r'<span class="\1">', text)
        text = replace(r'</:([^>]*)>', r'</span>', text)

        entry_tuple = {'key': key,
                       'year': year,
                       'text': text,
                       'bibtex': bib_buf.getvalue(),
                       'pdf': pdf,
                       'slides': slides,
                       'poster': poster}
        entry_tuple.update(entry.fields)

        publications.append(entry_tuple)

        for tag in tags:
            publications_lists[tag].append(entry_tuple)

        if not tags and untagged_title:
            publications_untagged.append(entry_tuple)

    # append untagged list if title is given
    if untagged_title and publications_untagged:
        publications_lists[untagged_title] = publications_untagged


    # output
    generator.context['publications'] = publications
    generator.context['publications_lists'] = publications_lists


class Bibliography(Directive):
    """
    Directive to embed bibliographies into articles/posts.

    Usage::

        .. bibliography:: PUBLICATIONS_SRC
          :template: TEMPLATE_NAME (optional)
          :options: TEMPLATE_OPTIONS_DICT (optional)
          :class: CLASS_NAME (optional)
          :filter_tag: FILTER_TAG (optional)
          :pybtex_style_args: PYBTEX_STYLE_ARGS (optional)
          :sorting_style: PYBTEX_SORTING_STYLE (optional)
          :abbreviate_names: PYBTEX_ABBREVIATE_NAMES (optional)
          :name_style: PYBTEX_NAME_STYLE (optional)

    e.g.::

        .. bibliography:: osm.bib
          :template: publications_unsrt
          :options: {'groupby_value': year}
          :class: my-bib
          :pybtex_style_args: {'sorting_style': 'author_year_title',
                               'abbreviate_names': False,
                               'name_style': 'lastfirst' }
          :sorting_style: author_year_title
          :abbreviate_names: False
          :name_style: lastfirst
    """
    required_arguments = 0
    optional_arguments = 100
    final_argument_whitespace = False
    has_content = True

    generator = None

    def set_generator(generator):
        Bibliography.generator = generator

    def boolean(argument):
        if argument=='True': return True
        if argument=='False': return False
        raise ValueError('must be boolean')
    option_spec = {
        'template': directives.unchanged,
        'options': directives.unchanged,
        'class': directives.class_option,
        'filter_tag': directives.unchanged,
        'pybtex_style_args': directives.unchanged,
        'sorting_style': directives.unchanged,
        'abbreviate_names': boolean,
        'name_style': directives.unchanged
    }

    def run(self):
        refs_files = self.arguments
        refs_string = '\n'.join(self.content)
        template_name = self.generator.settings.get('PUBLICATIONS_DEFAULT_TEMPLATE', 'bibliography')
        template_options = {}
        classes = [ 'bibliography' ]
        filter_tag = None
        pybtex_style_args = {}

        # fetch arguments
        if refs_files:
            classes += (basename(file) for file in refs_files)
        if 'template' in self.options:
            template_name = self.options['template']
        if 'options' in self.options:
            template_options = literal_eval(self.options['options'])
        if 'class' in self.options:
            classes = self.options['class']
        if 'filter_tag' in self.options:
            filter_tag = self.options['filter_tag']
        if 'pybtex_style_args' in self.options:
            pybtex_style_args.update(literal_eval(self.options['pybtex_style_args']))
        if 'sorting_style' in self.options:
            pybtex_style_args['sorting_style'] = self.options['sorting_style']
        if 'abbreviate_names' in self.options:
            pybtex_style_args['abbreviate_names'] = self.options['abbreviate_names']
        if 'name_style' in self.options:
            pybtex_style_args['name_style'] = self.options['name_style']

        # BibTeX input is a bib file or the directives content
        if not self.content and not refs_files:
            raise self.error('No BibTeX input source given.')

        refs_files = (self.get_pelican_path(file) for file in refs_files)

        # create a copy of generator context (don't mess up original context)
        original_context = self.generator.context
        self.generator.context = self.generator.context.copy()

        try:
            # add publications to generator.context
            self.generator.context.update(template_options)
            add_publications_to_context(self.generator, refs_files, refs_string, pybtex_style_args)

            # if applicable, return only publications containing a specific tag
            if filter_tag:
                self.generator.context['publications'] = self.generator.context['publications_lists'][filter_tag]

            # find template & generate HTML
            template = self.generator.get_template(template_name)
            html = template.render(self.generator.context)

        except Exception as e:
            raise self.error('Error rendering template `{}` ({}). '.format(template_name, e))
        finally:
            # restore original context
            self.generator.context = original_context

        # return container with HTML content
        node = nodes.raw(text = html, format='html')
        container = nodes.container(classes = classes)
        container.append(node)
        return [ container ]

    def get_pelican_path(self, path):
        """ determine actual absolute path in Pelican context """
        if path.startswith('/') or path.startswith(path_separator):
            # absolute path => relative to Pelican working directory
            path = join(self.generator.path, path[1:])
        else:
            # relative path => relative to directory of
            # source file using the directive
            source, line = self.state_machine.get_source_and_line(self.lineno)
            source_dir = dirname(abspath(source))
            path = join(source_dir, path)
        path = nodes.reprunicode(path)
        path = abspath(path)
        return path


def register():
    signals.generator_init.connect(generator_init)

    signals.article_generator_preread.connect(Bibliography.set_generator)
    signals.page_generator_preread.connect(Bibliography.set_generator)
    signals.static_generator_preread.connect(Bibliography.set_generator)

    directives.register_directive('bibliography', Bibliography)
