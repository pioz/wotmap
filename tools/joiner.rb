require 'mini_magick'

TILES_DIR = 'tiles'
COLS = 58
ROWS = 31
TILE_WIDTH  = 256
TILE_HEIGHT = 256
OUT = 'map.jpg'

MiniMagick::Tool.new('montage') do |m|
  (0...ROWS).each do |y|
    (0...COLS).each do |x|
      path = File.join(TILES_DIR, format("tile_%02d_%02d.jpg", x, y))
      if File.exist?(path)
        m << path
      else
        # Set size for the next generated canvas and push a white placeholder
        m.size "#{TILE_WIDTH}x#{TILE_HEIGHT}"
        m << "xc:white"
      end
    end
  end
  m.geometry "+0+0"
  m.tile "#{COLS}x#{ROWS}"
  m.background "white"
  m << OUT
end
