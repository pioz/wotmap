require 'fileutils'

source_dir = "to_check"
dest_dir   = "tiles"
mapping_file = "mapping.txt"

File.foreach(mapping_file) do |line|
  next unless line =~ /(tile_\d+\.jpg)\s*->\s*(tile_\d+_\d+\.jpg)/

  source_file = File.join(source_dir, $1)
  dest_file   = File.join(dest_dir, $2)

  FileUtils.mkdir_p(File.dirname(dest_file))

  if File.exist?(source_file)
    FileUtils.cp(source_file, dest_file)
  else
    puts "Warning: source file not found: #{source_file}"
  end
end
