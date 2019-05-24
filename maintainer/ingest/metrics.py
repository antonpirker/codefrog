from ingest.git import fetch_code_metrics


def code_metrics(project, start_date=None):
    # git url aus project, und clonen (wenn noch nicht da)

    # pull newest version of repo (hier oder wo anders?)

    # get start date (from param or repo)
    start_date = start_date

    # get end date (from repo)
    end_date = None

    # split time range in chunks.
    fetch_code_metrics(project, start_date, end_date).apply_async()

    # async task for every chunk.
        # - eintrag neu anlegen oder überschreiben

    # TODO: wie kann ich paralelle dann step2 machen? w
    #  arten bis alle chunks fertig sind? oder der reiche nach?
    #  immer ein chunk und dann ein step2? dann bringen die chunks nichts.
    #  ein ding der reihe nach und dort drinnen dann chunks machen und nach jedem chung den step2 anstoßen?

    pass


def issue_metrics(project, start_date=None):

    # check if github credetials in project

    # get start date (from param or repo)

    # async task that starts looping over api pages. (gib credentials mit)
        # - eintrag neu anlegen oder überschreiben

    pass