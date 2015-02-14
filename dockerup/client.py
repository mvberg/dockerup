#!/usr/bin/python2.7

import logging
import abc

class DockerClient(object):

	__metaclass__ = abc.ABCMeta

	def __init__(self):

		self.image_cache = []
		self.container_cache = []

		self.log = logging.getLogger(__name__)

	def flush_images(self):
		self.image_cache = []

	def flush_containers(self):
		self.container_cache = []

	def flush(self):
		self.flush_images()
		self.flush_containers()

	def refresh(self):
		self.image_cache = self.docker_images()
		self.container_cache = self.docker_containers()

	def tag(self, image):
		parts = image.split(':')
		repo = parts[0]
		if len(parts) > 1:
			tag = parts[1]
		else:
			tag = 'latest'
		return (repo, tag)

	def image(self, name=None, id=None):

		if name:
			(repo, tag) = self.tag(name)

		for image in self.images():

			if name and (repo != image['Repository'] or tag != image['Tag']):
				continue

			if id and id != image['Id']:
				continue

			return image

		return None

	def images(self):

		if not len(self.image_cache):
			self.image_cache = self.docker_images()

		return self.image_cache

	def container(self, image=None):

		for container in self.containers():
			if image is None or image == container['Image']:
				return container

		return None

	def containers(self):

		if not len(self.container_cache):
			self.container_cache = self.docker_containers()

		return self.container_cache

	def pull(self, image):

		try:
			self.log.debug('Pulling image: %s', image)
			if self.docker_pull(image):
				self.log.debug('Updated image found')
				self.flush_images()
				return True
			self.log.debug('Image is up to date')
		except Exception as e:
			self.log.debug('Pull failed: ' + e.message)
			# Missing image probably, just return false
			pass

		return False

	# Run a new container
	def run(self, image, **kwargs):

		kwargs.extend({
			'restart-policy': 'always',
			'image': image,
			'detach': True
		})

		self.log.debug('Running container: %s' % image)
		container = self.docker_run(**kwargs)
		self.log.info('Started container: %s' % container)
		self.flush_containers()

		return container

	# Start existing container
	def start(self, container):
		self.log.debug('Starting container: %s', container)
		self.docker_start(container)
		self.flush_containers()

	# Restart running container
	def restart(self, container):
		self.log.debug('Restarting container: %s', container)
		self.docker_restart(container)
		self.flush_containers()

	# Stop running container
	def stop(self, container, remove=True):
		self.log.debug('Stopping container: %s', container)
		self.docker_stop(container)
		if remove:
			self.rm(container)
		self.flush_containers()

	# Remove container
	def rm(self, container):
		self.log.debug('Removing stopped container: %s' % container)
		self.docker_rm(container)
		self.flush_containers()

	# Remove image
	def rmi(self, image):
		self.log.debug('Removing image: %s' % image)
		self.docker_rmi(image)
		self.flush_images()

	# Cleanup stopped containers and unused images
	def cleanup(self, images=True):

		# Always refresh state before cleanup
		self.flush()

		for container in self.containers():
			if not container['running']:
				self.rm(container['id'])
		
		for dangling in self.docker_images(filters={'dangling': 'true'}):
			self.rmi(dangling['id'])

	"""
	Subclass implementations
	"""

	@abc.abstractmethod
	def docker_images(self, filters=None):
		return []

	@abc.abstractmethod
	def docker_containers(self):
		return []

	@abc.abstractmethod
	def docker_pull(self, image):
		return False

	@abc.abstractmethod
	def docker_run(self, entry):
		return None

	@abc.abstractmethod
	def docker_start(self, container, entry):
		pass

	@abc.abstractmethod
	def docker_restart(self, container):
		pass

	@abc.abstractmethod
	def docker_stop(self, container):
		pass

	@abc.abstractmethod
	def docker_rm(self, container):
		pass

	@abc.abstractmethod
	def docker_rmi(self, image):
		pass
