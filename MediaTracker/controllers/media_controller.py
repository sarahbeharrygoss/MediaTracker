from MediaTracker.flask_app_and_db import db
from MediaTracker import models
from MediaTracker.controllers import tag_controller


# database i/o
# media


def get_all_media(tag_id=None, sort=None):
    if tag_id:
        media_list = tag_controller.get_tag(tag_id).tagged_media
    else:
        media_list = models.Media.query.all()

    if sort == "name":
        return sorted(media_list, key=lambda media: media.name)
    elif sort == "dateAdded":
        return sorted(media_list, key=lambda media: media.id)
    elif sort == "episode":
        return sorted(media_list,
                      key=lambda media: (media.current_episode.episode_number if media.current_episode else 0),
                      reverse=True)
    else:  # default sort is dateModified
        if all([media.last_updated for media in media_list]):
            return sorted(media_list, key=lambda media: media.last_updated, reverse=True)
        else:
            # can't sort by dateModified because some entries appear not to have one
            return media_list


def get_media(media_id):
    return models.Media.query.filter_by(id=media_id).first()


def add_media(media):
    db.session.add(media)
    db.session.commit()


def edit_media(media_id, name, current_episode_id, notes, tag_id_list):
    media = get_media(media_id)
    if media:
        media.name = name
        media.current_episode_id = current_episode_id
        media.notes = notes

        media.tags = tag_controller.convert_to_tags(tag_id_list)

        update_media(media)


def update_media(media):
    db.session.merge(media)
    db.session.commit()


def delete_media(media_id):
    media = get_media(media_id)
    if media:
        media.current_episode_id = None
        db.session.merge(media)
        get_episodes_for_media_query(media_id).delete(synchronize_session='fetch')
        db.session.delete(media)
        db.session.commit()
        return True
    else:
        return False


# episode


def get_episodes_for_media_query(media_id):
    return models.Episode.query.filter_by(media_id=media_id)


def increment_episode(media_id):
    media = get_media(media_id)
    if media.episodes:
        if media.current_episode:
            # Only change if this episode is not the last one
            i = iter(media.episodes)
            for item in i:
                if item.id == media.current_episode_id and item.id != media.episodes[-1].id:
                    media.current_episode_id = next(i).id
                    update_media(media)
                    return True
        else:
            # Current episode is the first one
            media.current_episode_id = iter(media.episodes).__next__().id
            update_media(media)
            return True
    return False


def add_episode(episode):
    db.session.add(episode)
    db.session.commit()


def delete_episode(episode_id):
    episode = models.Episode.query.filter_by(id=episode_id).first()
    if episode:
        # Check it's not the current episode of any series first
        media = models.Media.query.filter_by(current_episode_id=episode_id).first()
        if media:
            media.current_episode_id = None
            db.session.merge(media)
        db.session.delete(episode)
        db.session.commit()
        return True
    else:
        return False


# Generate n episodes 
def generate_episodes(media_id, count):
    media = get_media(media_id)
    if media.episodes:
        last_episode = media.episodes[-1]
        last_episode_number_floor = int(last_episode.episode_number)
    else:
        last_episode_number_floor = 0
    for i in range(last_episode_number_floor + 1, last_episode_number_floor + 1 + count):
        episode = models.Episode(episode_number=i,
                                 media_id=media_id)
        add_episode(episode)


def delete_all_episodes(media_id):
    # Ensure the current episode does not reference episodes to be deleted
    media = get_media(media_id)
    media.current_episode_id = None
    db.session.merge(media)

    get_episodes_for_media_query(media_id).delete(synchronize_session='fetch')
    db.session.commit()
    return True
