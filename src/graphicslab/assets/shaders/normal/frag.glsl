#version 330

in vec4 vert_pos_view;
in vec4 vert_norm_world;
in vec4 vert_norm_view;

uniform mat4 mat_P;

out vec4 frag_color;

void main() {
  vec3 norm_color = vert_norm_world.xyz;
  norm_color = (norm_color + 1) / 2;
  frag_color = vec4(norm_color, 1);
}
