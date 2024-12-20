#version 330

in vec4 vert_pos_view;
in vec4 vert_norm_view;

out vec4 frag_color;

void main() {
  vec4 vert_norm_color = vec4(vert_norm_view.xyz, 1);
  frag_color = (vert_norm_color + 1) / 2;
  // frag_color = vec4(1, 1, 1, 1);
}
