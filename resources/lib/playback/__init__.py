"""Playback: an episode page becomes a stream, a channel becomes a DRM session.

Two paths, two modules: a clear HLS stream needs a URL and nothing else, a live
channel or a DRM film needs a token and a license. Keeping them apart means the
untestable one (Widevine, which the local Kodi cannot play) stays small.
"""
