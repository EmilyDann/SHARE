from share.normalize import Parser, Delegate, RunPython, ParseDate, ParseName, Normalizer, Map, ctx, Try, Subjects, DOI


class Email(Parser):
    email = ctx


class PersonEmail(Parser):
    email = Delegate(Email, ctx)


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if 'peerj.com' in link:
            return 'provider'
        return 'misc'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = Delegate(Subject, ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Publisher(Parser):
    name = ctx


class Institution(Parser):
    name = ctx


class Association(Parser):
    pass


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last


class Contributor(Parser):
    person = Delegate(Person, ctx)
    cited_name = ctx
    order_cited = ctx('index')


class CreativeWork(Parser):
    title = ctx.title
    description = Try(ctx.description)
    contributors = Map(Delegate(Contributor), ctx.author)
    links = Map(
        Delegate(ThroughLinks),
        ctx.pdf_url,
        DOI(ctx.doi),
        ctx.fulltext_html_url
    )
    publishers = Map(
        Delegate(Association.using(entity=Delegate(Publisher))),
        ctx.publisher
    )
    institutions = Map(
        Delegate(Association.using(entity=Delegate(Institution))),
        RunPython('get_author_institute', ctx)
    )
    date_published = ParseDate(ctx.date)
    language = ctx.language
    tags = Map(
        Delegate(ThroughTags),
        Try(ctx.keywords),
        Try(ctx.subjects)
    )
    subjects = Map(Delegate(ThroughSubjects), Subjects(ctx.subjects))

    class Extra:
        modified = ParseDate(ctx.date)
        subjects = Try(ctx.subjects)
        identifiers = ctx.identifiers
        volume = Try(ctx.volume)
        emails = Try(ctx.author_email)
        journal_title = Try(ctx.journal_title)
        journal_abbrev = Try(ctx.journal_abbrev)
        description_html = Try(ctx['description-html'])
        issn = Try(ctx.issn)

    def get_author_institute(self, context):
        # read into a set while preserving order and passed back to erase duplicates
        seen = set()
        if 'author_institution' in context:
            if isinstance(context['author_institution'], str):
                return [x for x in [context['author_institution']] if x not in seen and not seen.add(x)]
            return [x for x in context['author_institution'] if x not in seen and not seen.add(x)]
        # the below is author_institutions with an 's', it will always be a string
        # and is sometimes present in the case that author_institution is not.
        # This will always be a string
        return [x for x in context['author_institutions'].split('; ') if x not in seen and not seen.add(x)]


class Preprint(CreativeWork):

    class Extra:
        modified = RunPython('parse_date', ctx.date)
        subjects = ctx.subjects
        identifiers = Try(ctx.identifiers)
        emails = Try(ctx.author_email)
        description_html = Try(ctx['description-html'])


class PeerJNormalizer(Normalizer):

    def do_normalize(self, data):
        unwrapped = self.unwrap_data(data)
        if 'preprint' in unwrapped['_links']['self']['href']:
            return Preprint(unwrapped).parse()
        return CreativeWork(unwrapped).parse()
