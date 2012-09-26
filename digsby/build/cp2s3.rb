#!/bin/env ruby

# This file is released under the MIT license.
# Copyright (c) Famundo LLC, 2007. http://www.famundo.com
# Author: Guy Naor - http://devblog.famundo.com

require 'optparse'

# Parse the options
@buckets = []
@compress = []
@verbose = 0
opts = OptionParser.new do |opts|
  opts.banner =  "Usage: cp2s3.rb [options] FILE_SPEC"
  opts.separator "Copy files and directories from the local machine into Amazon's S3. Keep the directory structure intact."
  opts.separator "Empty directories will be skipped."
  opts.separator ""
  opts.separator "FILE_SPEC  List of files/directories. Accepts wildcards."
  opts.separator "           If given the -g option, interpret FILE_SPEC as a Ruby Dir::Glob style regular expressions."
  opts.separator "           With -g option, '' needed around the pattern to protect it from shell parsing."
  opts.separator ""
  opts.separator "Required:"
  opts.on("-k", "--key ACCESS_KEY"    , "Your S3 access key. You can also set the environment variable AWS_ACCESS_KEY_ID instead") { |o| @access_key = o }
  opts.on("-s", "--secret SECRET_KEY" , "Your S3 secret key. You can also set the environment variable AWS_SECRET_ACCESS_KEY instead") { |o| @secret_key = o }
  opts.on("-b", "--bucket BUCKET_NAME", "The S3 bucket you want the files to go into. Repeat for multiple buckets.") { |o| @buckets << o }

  opts.separator ""
  opts.separator "Optional:"

  opts.on("-x", "--remote-prefix PREFIX", "A prefix to add to each file as it's uploaded") { |o| @prefix = o }
  opts.on("-v", "--verbose", "Print the file names as they are being copied. Repeat for more details") { |o| @verbose += 1 }
  opts.on("-p", "--public-read", "Set the copied files permission to be public readable.") { |o| @public = true }
  opts.on("-c", "--compress EXT", "Compress files with given EXT before uploading (ususally css and js),", "setting the HTTP headers for delivery accordingly. Repeat for multiple extensions") { |o| @compress << ".#{o}" }
  opts.on("-a", "--compress-all", "Compress all files. Using this option will use the compress option (-c, --compress) as a black list of files to compress (instead of a whitelist).") { |o| @compressall = true }
  opts.on("-d", "--digest", "Save the sha1 digest of the file, to the S3 metadata. Require sha1sum to be installed") { |o| @save_hash  = true }
  opts.on("-t", "--time", "Save modified time of the file, to the S3 metadata") { |o| @save_time  = true }
  opts.on("-z", "--size", "Save size of the file, to the S3 metadata ") { |o| @save_size  = true }
  opts.on("-r", "--recursive", "If using file system based FILE_SPEC, recurse into sub-directories") { |o| @fs_recurse  = true }
  opts.on("-g", "--glob-ruby", "Interpret FILE_SPEC as a Ruby Dir::Glob. Make sure to put it in ''") { |o| @ruby_glob  = true }
  opts.on("-m", "--modified-only", "Only upload files that were modified must have need uploaded with the digest option.", "Will force digest, size and time modes on") { |o| @modified_only = @save_hash = @save_time = @save_size = true; }
  opts.on("-y", "--dry-run", "Simulate only - do not upload any file to S3") { |o| @dry_run  = true }
  opts.on("-h", "--help", "Show this instructions") { |o| @help_exit  = true }
  opts.separator ""
  opts.banner =  "Copyright(c) Famundo LLC, 2007 (www.famundo.com). Released under the MIT license."
end

@file_spec = opts.parse!(ARGV)

@access_key ||= ENV['AWS_ACCESS_KEY_ID']
@secret_key ||= ENV['AWS_SECRET_ACCESS_KEY']
@prefix ||= ''

if @help_exit || !@access_key || !@secret_key || @buckets.empty? || !@file_spec || @file_spec.empty?
  puts opts.to_s
  exit
end

# Now we start working for real
require 'rubygems'
require 'aws/s3'
include AWS::S3
require 'fileutils'
require 'stringio'
require 'zlib'

# Log to stderr according to verbosity
def log message, for_level
  puts(message) if @verbose >= for_level
end


# Connect to s3
log "Connecting to S3", 3
AWS::S3::Base.establish_connection!(:access_key_id => @access_key, :secret_access_key => @secret_key)
log "Connected!", 3

# Copy one file to amazon, compressing and setting metadata as needed
def copy_one_file file, fstat
  compressed = nil
  content_encoding = nil
  log_prefix = ''

  # Store it!
  options = {}
  options[:access] = :public_read if @public
  options["x-amz-meta-sha1_hash"] = `sha1sum #{file}`.split[0] if @save_hash
  options["x-amz-meta-mtime"] = fstat.mtime.getutc.to_i if @save_time
  options["x-amz-meta-size"] = fstat.size if @save_size

  sent_it = !@modified_only
  @buckets.each do |b|
    # Check if it was modified
    if @modified_only
      begin
	if S3Object.find("#{@prefix}#{file}", b).metadata["x-amz-meta-sha1_hash"] == options["x-amz-meta-sha1_hash"]
	  # No change - go on
	  log("Skipping: #{file} in #{b}", 3)
	  next
	end
      rescue AWS::S3::NoSuchKey => ex
	# This file isn't there yet, so we need to send it
      end
    end

    # We compress only if we need to compredd and we didn't compress yet
    if @compressall || (!@compress.empty? && compressed.nil?)
      if (@compressall && !@compress.include?(File.extname(file))) || (!@compressall && @compress.include?(File.extname(file)))
	# Compress it
	log "Compressing #{file}", 3
	strio = StringIO.open('', 'wb')
	gz = Zlib::GzipWriter.new(strio)
	gz.write(open(file, 'rb').read)
	gz.close
	compressed = strio.string
        options["Content-Encoding"] = 'gzip'
	log_prefix = '[c] ' if @verbose == 2 # Mark as compressed
      elsif @verbose == 2
	log_prefix = '[-] ' # So the file names align...
      end
    end

    log("Sending #{file} to #{b}...", 3)
    the_real_data = compressed.nil? ? open(file).read : compressed
    S3Object.store("#{@prefix}#{file}", the_real_data, b, options) unless @dry_run
    sent_it = true
  end
  log("#{log_prefix}#{file}", 1) if sent_it
end

# Copy one file/dir from the system, recurssing if needed. Used for non-Ruby style globs
def copy_one_file_or_dir name, base_dir
  return if name[0,1] == '.'
  file_name = "#{base_dir}#{name}"
  fstat = File.stat(file_name)
  copy_one_file(file_name, fstat) if fstat.file? || fstat.symlink?
  # See if we need to recurse...
  if @fs_recurse && fstat.directory?
    my_base = file_name + '/'
    Dir.foreach(my_base) {
      |e|
      i = 0
      error = false
      success = false
      until i == 5 or success
        begin
          copy_one_file_or_dir(e, my_base)
	rescue StandardError => error
	  i += 1
          log("#{e} failed #{i} times", 0)
        else
          success = true
        end
      end
      raise error unless success
    }
  end
end


# Glob all the dirs for the files to upload - we expect a ruby like glob format or file system list from the command line
@file_spec.each do |spec|
  if @ruby_glob
    # Ruby style
    Dir.glob(spec) do |file|
      fstat = File.stat(file)
      copy_one_file(file, fstat) if fstat.file? || fstat.symlink?
    end
  else
    # File system style
    copy_one_file_or_dir(spec, '')
  end
end

